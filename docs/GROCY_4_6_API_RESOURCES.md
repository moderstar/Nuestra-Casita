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
| `tasks` | Planned | Household task definitions |
| `task_categories` | Implemented | Task category master data |
| `product_groups` | Implemented | Product group master data |
| `equipment` | Planned | Equipment master data |
| `api_keys` | Not Applicable | Security credentials |
| `userfields` | Implemented | Declarative custom field definitions; per-object values are excluded |
| `userentities` | Planned | Custom entity definitions |
| `userobjects` | Planned | Custom entity records |
| `meal_plan` | Planned | Meal-plan entries |
| `stock_log` | Not Applicable | Read-only stock journal |
| `stock` | Not Applicable | Runtime stock state |
| `stock_current_locations` | Not Applicable | Derived stock-location view |
| `chores_log` | Not Applicable | Chore execution journal |
| `meal_plan_sections` | Planned | Meal-plan section definitions |
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
