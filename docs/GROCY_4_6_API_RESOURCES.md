# Grocy 4.6 API Resource Inventory

This inventory tracks the native entities exposed through Grocy 4.6's
generic `/objects/{entity}` API and Nuestra Casita's synchronization status.
It is based on the `ExposedEntity` schema in Grocy's tagged
`v4.6.0` OpenAPI specification.

Status meanings:

- **Implemented**: Registered in Nuestra Casita and included in `sync all`.
- **Read capability**: Normalized for application and CLI reads but excluded
  from declarative synchronization because the backend owns live activity.
- **Planned**: A native Grocy resource that may be synchronized in a future
  milestone.
- **Not Applicable**: Runtime, derived, security, journal, or internal data
  that should not be managed from an authoritative synchronization catalog.

| Grocy entity | Status | Notes |
| --- | --- | --- |
| `products` | Implemented | Product master data |
| `chores` | Implemented | Recurring chore definitions; execution state is excluded |
| `product_barcodes` | Implemented | Managed barcode-to-Product associations |
| `batteries` | Implemented | Battery definitions; charge history is excluded |
| `locations` | Implemented | Stock locations |
| `quantity_units` | Implemented | Quantity unit master data |
| `quantity_unit_conversions` | Implemented | Managed directional global and Product-specific conversion rules |
| `shopping_list` | Read capability | Grocy-owned runtime items; never synchronized from Git |
| `shopping_lists` | Read capability | Named lists grouped with their current items |
| `shopping_locations` | Implemented | Shopping stores and locations |
| `recipes` | Implemented | Declarative Recipe definitions; ingredients and runtime serving state are excluded |
| `recipes_pos` | Implemented | Declarative Recipe ingredients; fulfillment and calculated state are excluded |
| `recipes_nestings` | Planned | Nested recipe relationships |
| `tasks` | Implemented | Managed non-recurring definitions; completion remains Grocy-owned |
| `task_categories` | Implemented | Task category master data |
| `product_groups` | Implemented | Product group master data |
| `equipment` | Implemented | Definitions; manuals and Userfield values are excluded |
| `api_keys` | Not Applicable | Security credentials |
| `userfields` | Implemented | Declarative custom field definitions; per-object values are excluded |
| `userentities` | Implemented | Definition metadata only |
| `userobjects` | Not Applicable | Live custom records and values remain Grocy-owned |
| `meal_plan` | Implemented | Managed recipe, product, and note entries; completion remains Grocy-owned |
| `stock_log` | Not Applicable | Read-only stock journal |
| `stock` | Not Applicable | Runtime stock state |
| `stock_current_locations` | Not Applicable | Derived stock-location view |
| `chores_log` | Not Applicable | Chore execution journal |
| `meal_plan_sections` | Implemented | Named section definitions and presentation ordering/time |
| `products_last_purchased` | Not Applicable | Derived reporting view |
| `products_average_price` | Not Applicable | Derived reporting view |
| `quantity_unit_conversions_resolved` | Not Applicable | Derived conversion view |
| `recipes_pos_resolved` | Not Applicable | Derived recipe-position view |
| `battery_charge_cycles` | Not Applicable | Battery charge journal |
| `product_barcodes_view` | Not Applicable | Derived barcode view |
| `permission_hierarchy` | Not Applicable | Internal permission metadata |

Grocy 4.6 does not expose a `chore_groups` entity. Task Categories replace
the previously assumed Chore Groups milestone because they are a native,
supported Grocy resource.

## Equipment API Findings

Grocy 4.6 exposes Equipment through generic `GET`, `POST`, `PUT`, and `DELETE`
object endpoints under `/objects/equipment`. The table requires a unique
`name` and also contains `description`, `instruction_manual_file_name`, an ID,
and `row_created_timestamp`. The UI uploads manuals separately through the
files API; no native Equipment category, Location, purchase, warranty, or
maintenance-history relationship exists in this entity. Additional metadata
can be modeled through the separate Userfields mechanism.

Nuestra Casita matches normalized names, creates cataloged definitions, and
updates descriptions. It never deletes Equipment or changes manual references,
timestamps, or Userfield values.

## User Entity API Findings

Grocy 4.6 exposes definitions at `/objects/userentities`. A definition has a
unique internal `name`, required `caption`, optional `description`, sidebar
visibility, icon CSS class, generated ID, and creation timestamp. The frontend
uses generic POST and PUT operations but disables the internal name when
editing, so Nuestra Casita treats it as immutable.

User Entity fields are ordinary `userfields` definitions whose entity is
`userentity-<name>`. Instance records are separate `/objects/userobjects` rows
linked by `userentity_id`, and their values are held in Grocy's Userfield value
store. Definition synchronization never writes records or values. Although
Grocy exposes generic deletes, Nuestra Casita never invokes them. Renames,
field-type changes, record migration, and definition deletion are unsupported
because they can orphan or reinterpret existing custom data.

## Grocy Integration — Dashboard Readiness

| Capability | Dashboard API status |
| --- | --- |
| Inventory read | Implemented and normalized |
| Shopping Lists read | Implemented, including named/empty lists and items |
| Recipes read | Implemented and normalized |
| Meal Plan read | Implemented and normalized |
| Chores read | Implemented and normalized |
| Tasks read | Implemented and normalized |
| Dashboard snapshot assembly | Implemented with versioned backend-neutral contract |
| API transport | Implemented as versioned read-only FastAPI endpoints |
| Authentication | Signed HTTP-only cookie session implemented |
| Docker deployment | Dedicated non-root Dashboard API service implemented |

Milestone 16 can build the iPad browser interface against the authenticated
API. Caching or a new database remains unnecessary until measured behavior
demonstrates that need.

## Interactive Shopping and Chore Findings

Grocy 4.6 stores list definitions in `shopping_lists` and live entries in the
separate `shopping_list` entity. Nuestra Casita uses the generic object create,
update, and delete endpoints for exact live items. Product entries reference a
Product and its purchase quantity unit; note-only entries have neither. Named
lists remain independent.

The `done` field is only the Shopping UI's purchased marker and does not book
stock. Decimal amounts are sent as decimal strings. Grocy 4.6's specialized
shopping add/remove-product routes have a decimal truncation defect fixed in
4.7, so this integration deliberately uses the generic object API.

Chore completion uses `POST /chores/{choreId}/execute` and then refreshes the
authoritative projections. Chore creation remains with the Git-managed catalog
and sync workflow. The dashboard exposes no generic write proxy and performs
no stock booking, bulk deletion, chore deletion, or Task completion.

## Product Barcode API Findings

Grocy 4.6 exposes `product_barcodes` through the generic object endpoints:

- `GET` and `POST /objects/product_barcodes`
- `GET`, `PUT`, and `DELETE /objects/product_barcodes/{id}`

The native model requires `product_id` and the string `barcode`. It can also
store optional purchase metadata (`qu_id`, `amount`, `shopping_location_id`,
`last_price`, and `note`). A Product may have multiple barcode rows, while a
barcode is unique and therefore cannot belong to multiple Products. Version
4.6 also matches barcode values case-insensitively. The API does not publish
a supported-format or checksum constraint, so Nuestra Casita treats barcode
values as opaque strings and preserves leading zeros.

This milestone manages only barcode-to-Product associations. Optional
purchase metadata and deletes are deliberately unsupported. Although the
generic API permits updates and deletes, synchronization refuses to reassign
an existing barcode and never deletes a row absent from Git. These rules avoid
overwriting unmanaged Grocy barcode data.

## Tasks API Findings

Grocy 4.6 stores non-recurring Tasks in the native `tasks` entity. Definition
records are available through the generic object API:

- `GET` and `POST /objects/tasks`
- `GET`, `PUT`, and `DELETE /objects/tasks/{id}`

The entity fields are `id`, required `name`, optional `description`, optional
`due_date`, `done`, `done_timestamp`, optional `category_id`, optional
`assigned_to_user_id`, and `row_created_timestamp`. The specialized
`GET /tasks` endpoint returns only incomplete Tasks and expands the assigned
user and Task Category. `POST /tasks/{taskId}/complete` and
`POST /tasks/{taskId}/undo` exclusively manage completion state.

Nuestra Casita reads `/objects/tasks` so completed rows remain visible for
identity matching, but it never manages `done` or `done_timestamp`. The catalog
supports `name`, `description`, a date-only due date, and an optional Task
Category. Assignment is deferred because Grocy represents it with
instance-specific user IDs. Userfields, creation timestamps, specialized
completion endpoints, and delete operations are also outside this milestone.
Grocy 4.6 has no separate Task history entity: completion is current state on
the Task row, changed only through the complete and undo operations. Nuestra
Casita does not call either operation.

Grocy has no external Task key and does not enforce a unique Task name. Exact,
case-insensitive normalized name matching is therefore the conservative
identity rule. Duplicate catalog names or duplicate matching Grocy names are
reported as ambiguity instead of being updated.

## Meal Planning API Findings

Grocy 4.6 exposes both `meal_plan_sections` and `meal_plan` through the generic
object read, create, update, and delete endpoints. Nuestra Casita uses only
read, create, and controlled update operations.

Meal Plan Sections contain a unique `name`, optional `sort_number`, optional
`time_info`, generated ID, and creation timestamp. Grocy also maintains an
internal blank section with ID `-1`; synchronization filters that row and never
manages or deletes it. The section name is the stable normalized identity.

Meal Plan Entries contain a required `day`, a `type` of `recipe`, `product`, or
`note`, and a required `section_id`. Recipe entries use `recipe_id` and
`recipe_servings`; Product entries use `product_id`, `product_amount`, and
`product_qu_id`; note entries use `note`. The `done` flag is live activity and
is excluded from catalog payloads. `row_created_timestamp` is generated and is
also excluded.

Grocy provides no external entry key, uniqueness constraint, ordering field,
entry time field, template entity, or recurring meal-plan API. The UI's copy
day behavior creates ordinary entries rather than a reusable template.

The conservative identity is day, section, type, and the type-specific Recipe,
Product, or exact note content. This permits multiple different entries in one
section on one day. Duplicate identities in Git or Grocy are ambiguous and
rejected. Safe updates are limited to Recipe servings and Product amount/unit;
changing the day, section, type, reference, or note produces a distinct create
without modifying the pre-existing Grocy row.
