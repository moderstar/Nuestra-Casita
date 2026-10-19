# Nuestra Casita Architecture

Nuestra Casita is a backend-neutral household orchestration platform. Grocy
synchronization is its first integration, not the platform boundary.

The core architecture is documented in:

- [CORE_ARCHITECTURE.md](CORE_ARCHITECTURE.md)
- [APPLICATION_LAYER.md](APPLICATION_LAYER.md)
- [COMPOSITION_ROOT.md](COMPOSITION_ROOT.md)
- [GROCY_READ_ADAPTER.md](GROCY_READ_ADAPTER.md)
- [INTEGRATION_CONTRACT.md](INTEGRATION_CONTRACT.md)
- [DASHBOARD_CONTRACT.md](DASHBOARD_CONTRACT.md)
- [COMMAND_FRAMEWORK.md](COMMAND_FRAMEWORK.md)

The foundational code packages are:

- `casita.domain`: immutable household models
- `casita.integrations`: external-system and synchronization contracts
- `casita.application`: household services and dashboard assembly
- `casita.bootstrap`: explicit application construction and object lifetime
- `casita.dashboard`: the internal kitchen-dashboard data contract

The existing Grocy implementation remains unchanged and operational while a
Grocy read adapter translates runtime data into platform domain models.

## Application Command Flow

The unified CLI follows the platform dependency boundary:

`CLI → Application Services → Planner / Executor Protocols → Backend
Registry → Integration Contracts → Active Backend`

Dashboard, doctor, inventory, recipes, synchronization, and preserved
maintenance commands all enter through application services. The
`shopping-lists` command uses the existing `ShoppingService` and read
contract. The CLI does not
import the Grocy client or synchronization engine. The composition root
constructs one Grocy client and registers a `GrocyBackendProvider`.
`BackendResolver` selects Grocy as the unchanged default, and the provider
supplies integrations plus planner/executor implementations to the
composition root.

## Grocy Read Integration

`casita.integrations.grocy.GrocyReadAdapter` implements the backend-neutral
`Integration` contract for Inventory, Shopping, Recipes, and Chores. Native
Grocy responses are translated inside the adapter package and never reach
application services.

`casita.bootstrap.build_grocy_application()` explicitly constructs and
registers the adapter, assigns capability ownership, and returns the same
backend-neutral application graph used by every future integration.

The read adapter and synchronization engine share the authenticated
`GrocyApiClient`. Synchronization behavior and resource registration remain
unchanged.

See [GROCY_READ_ADAPTER.md](GROCY_READ_ADAPTER.md) for endpoint mappings,
identity handling, and current limitations.

## Shopping Lists

`python tools/casita.py shopping-lists` reads named Grocy 4.6 Shopping Lists,
their current items, Products, and Quantity Units through the Shopping
capability. It renders normalized models only; the CLI never calls Grocy
directly.

Shopping-list definitions and live items are distinct native entities. Live
item state—including amount, note, completion, membership, and removal—is
owned by Grocy and is not declaratively synchronized from Git. This prevents
catalog synchronization from overwriting household shopping activity.

## Grocy Integration Architecture

The current Grocy integration uses registered resource definitions to
synchronize version-controlled catalogs with Grocy.

The synchronization flow is:

1. Load a resource definition from `casita.registry`.
2. Load its CSV catalog and Grocy endpoint through `casita.sync_engine`.
3. Match objects by normalized or resource-defined identity and build a
   create, update, or match plan.
4. Display the plan without changing Grocy.
5. Apply the plan only when the user supplies `--apply`.

Resource definitions provide the catalog mapping, Grocy endpoint, comparison
function, payload builders, display names, and lookup requirements. The sync
and apply engines contain no Product- or Product-Group-specific API logic.

## Registered Resources

### Products

- Catalog: `catalog/products.csv`
- Grocy endpoint: `/objects/products`
- Requires Product Group, Location, and Quantity Unit lookups
- CLI: `python tools/casita.py sync products [--apply]`

### Product Barcodes

- Catalog: `catalog/product_barcodes.csv`
- Grocy endpoint: `/objects/product_barcodes`
- Identity: non-empty barcode string, matched case-insensitively
- Managed association: Barcode to Product name
- Requires Product lookups and runs after Products
- CLI: `python tools/casita.py sync product-barcodes [--apply]`

The resource creates explicitly cataloged associations and treats an existing
association as a match. It rejects duplicate identities and refuses to
reassign an existing barcode to another Product. Optional native purchase
metadata is outside the managed catalog. No update or delete operation is
planned, so Grocy-only barcode records remain untouched.

### Product Groups

- Catalog: `catalog/product_groups.csv`
- Grocy endpoint: `/objects/product_groups`
- Fields: `name`, `description`, and `active`
- Requires no lookup tables
- CLI: `python tools/casita.py sync product-groups [--apply]`

### Quantity Units

- Catalog: `catalog/quantity_units.csv`
- Grocy endpoint: `/objects/quantity_units`
- Fields: `name`, `name_plural`, `plural_forms`, `description`, and `active`
- Requires no lookup tables
- CLI: `python tools/casita.py sync quantity-units [--apply]`

### Quantity Unit Conversions

- Catalog: `catalog/quantity_unit_conversions.csv`
- Grocy endpoint: `/objects/quantity_unit_conversions`
- Identity: optional Product scope plus directional source and target units
- Managed field: positive decimal `factor`
- Requires Quantity Unit and optional Product lookups
- CLI: `python tools/casita.py sync quantity-unit-conversions [--apply]`

The direction is `1 From Quantity Unit = Factor To Quantity Units`. A blank
Product creates a global/default conversion; a Product name creates a
product-specific conversion for the same direction. Factors are parsed and
compared using `Decimal`, then serialized without binary floating-point
conversion.

The catalog owns only identities explicitly listed in Git. Existing Grocy
conversions absent from the catalog are preserved. Planning rejects missing
references, non-positive or non-finite factors, same-unit directions, and
duplicate or conflicting identities. Reverse and transitively resolved
conversions are Grocy-derived behavior and are not written as additional
catalog rows.

### Locations

- Catalog: `catalog/locations.csv`
- Grocy endpoint: `/objects/locations`
- Fields: `name`, `description`, `is_freezer`, and `active`
- Requires no lookup tables
- CLI: `python tools/casita.py sync locations [--apply]`

### Shopping Locations

- Catalog: `catalog/stores.csv`
- Grocy endpoint: `/objects/shopping_locations`
- Fields: `name`, `description`, and `active`
- Requires no lookup tables
- CLI: `python tools/casita.py sync shopping-locations [--apply]`

### Task Categories

- Catalog: `catalog/task_categories.csv`
- Grocy endpoint: `/objects/task_categories`
- Fields: `name`, `description`, and `active`
- Requires no lookup tables
- CLI: `python tools/casita.py sync task-categories [--apply]`

### Tasks

- Catalog: `catalog/tasks.csv`
- Grocy endpoint: `/objects/tasks`
- Managed fields: `name`, `description`, `due_date`, and `category_id`
- Exact normalized Task name identity; duplicate matches are rejected
- Optional Task Category lookup; runs after Task Categories
- CLI: `python tools/casita.py sync tasks [--apply]`

Tasks are non-recurring definitions, unlike Chores. Synchronization never
includes `done`, `done_timestamp`, `assigned_to_user_id`, creation timestamps,
or userfields. Completed Tasks remain matchable through the object endpoint,
and safe definition updates cannot reset their activity. Grocy-only Tasks are
preserved and automatic deletion is unsupported.

### Chores

- Catalog: `catalog/chores.csv`
- Grocy endpoint: `/objects/chores`
- Managed definition fields: `name`, `description`, `period_type`,
  `period_interval`, `period_days`, `period_config`, `track_date_only`,
  `rollover`, `consume_product_on_execution`, `product_id`,
  `product_amount`, and `active`
- `start_date` is required for creation but intentionally excluded from
  updates because Grocy treats it as immutable after the first execution
- Optional product consumption resolves `product_id` through the Products
  lookup
- Task Categories are not related to Chores in the native Grocy 4.6 schema
- CLI: `python tools/casita.py sync chores [--apply]`

Chore assignment fields are intentionally not managed. Grocy stores assigned
users as instance-specific IDs and recalculates the next assignment through a
separate operational API after edits. New synchronized Chores default to
`no-assignment`; existing assignment configuration remains untouched.

Chore runtime fields are also excluded: `next_execution_assigned_to_user_id`,
`rescheduled_date`, `rescheduled_next_execution_assigned_to_user_id`,
`row_created_timestamp`, and all `chores_log` execution history.

### Batteries

- Catalog: `catalog/batteries.csv`
- Grocy endpoint: `/objects/batteries`
- Managed definition fields: `name`, `description`, `used_in`,
  `charge_interval_days`, and `active`
- `charge_interval_days` must be a nonnegative integer; `0` disables
  next-charge suggestions
- Requires no lookup tables
- CLI: `python tools/casita.py sync batteries [--apply]`

Battery operational state is intentionally excluded. Charge history,
undo state, tracking timestamps, and calculated next-charge status are stored
in `battery_charge_cycles` or derived views rather than the Battery definition.

### Recipes

- Catalog: `catalog/recipes.csv`
- Grocy endpoint: `/objects/recipes?query[]=type=normal`
- Managed definition fields: `name`, `description`, `base_servings`,
  `not_check_shoppinglist`, and optional `product_id`
- `product_id` resolves the optional produced Product through the Products
  lookup
- New records explicitly use Grocy's native `normal` Recipe type
- CLI: `python tools/casita.py sync recipes [--apply]`

Recipe ingredients are intentionally deferred to the separate native
`recipes_pos` resource. Recipe Positions will depend on Recipes, Products,
and Quantity Units. Nested recipes are stored separately in
`recipes_nestings` and are also outside this milestone.

Recipe runtime and asset fields are excluded. `desired_servings` is mutable
serving-scale state used when consuming a Recipe, `picture_file_name` refers
to an externally stored file, and `row_created_timestamp` is generated by
Grocy. Derived costs, calories, fulfillment, and stock calculations are views
rather than Recipe definition fields.

### Recipe Positions

- Catalog: `catalog/recipe_positions.csv`
- Grocy endpoint: `/objects/recipes_pos`
- Managed ingredient fields: `recipe_id`, `product_id`, `amount`, `qu_id`,
  `only_check_single_unit_in_stock`, `variable_amount`, `round_up`,
  `not_check_stock_fulfillment`, `ingredient_group`, `note`, and
  `price_factor`
- Recipe, Product, and Quantity Unit relationships resolve through lookup
  tables
- CLI: `python tools/casita.py sync recipe-positions [--apply]`

Grocy Recipe Positions have no native name field. The generic planning engine
therefore supports optional resource identity and display-name functions while
retaining name-based matching as the default. Recipe Positions use the native
Recipe/Product relationship as their stable identity. A Recipe cannot contain
the same Product more than once in the authoritative catalog because those
rows would have the same identity.

`row_created_timestamp` is generated by Grocy and is not synchronized.
Fulfillment status, missing amounts, shopping-list state, calculated costs,
consumption history, and inventory calculations are runtime or derived data
and are intentionally excluded.

### Userfields

- Catalog: `catalog/userfields.csv`
- Grocy endpoint: `/objects/userfields`
- Managed definition fields: `entity`, `name`, `caption`, `type`, `config`,
  `sort_number`, `show_as_column_in_tables`, `input_required`, and
  `default_value`
- Uses Grocy's native unique identity of `entity` plus internal field `name`
- Requires no object-ID lookups
- CLI: `python tools/casita.py sync userfields [--apply]`

Grocy 4.6 supports Userfields for every entity in its `ExposedEntity` schema,
the special `users` entity, and dynamically defined entities named
`userentity-<name>`. Dynamic user-entity fields require the corresponding
User Entity to already exist in Grocy.

Supported native field types are checkbox, date, datetime, file, image, link,
link-with-title, integral/decimal/currency numbers, preset list/checklist,
and single-line/multiline text. `config` stores the declarative choices for
preset fields. `default_value` is meaningful only for date and datetime
fields, where Grocy 4.6 supports `now`.

Userfield values are intentionally not synchronized. They are mutable
per-object data stored separately in `userfield_values` and managed through
`/userfields/{entity}/{objectId}`. `row_created_timestamp` is generated by
Grocy and is also excluded.

Products use the same generic synchronization and apply engines as Product
Groups and the other registered resources.

## Complete Synchronization

The `sync all` command runs registered resources in dependency-aware order:

1. Userfields
2. Product Groups
3. Quantity Units
4. Locations
5. Shopping Locations
6. Products
7. Product Barcodes
8. Quantity Unit Conversions
9. Task Categories
10. Tasks
11. Chores
12. Batteries
13. Recipes
14. Recipe Positions

Each individual catalog operation is orchestrated by the backend-neutral
`CatalogApplicationService`. It validates the resource, coordinates structured
planning and optional execution through `CatalogPlanner` and
`CatalogExecutor`, and returns `CatalogOperationResult`. Planning produces a
`CatalogPlan` containing explicit `CatalogOperation` values; execution
produces `CatalogExecutionResult`.
`SynchronizationApplicationService` uses the same service for every resource
in `sync all`; neither service imports Grocy or renders terminal output.

The order is defined by `SYNC_RESOURCE_ORDER` in `casita.registry`, not by the
CLI. The orchestration workflow invokes the same synchronization function used
by each individual resource command.

- Dry run: `python tools/casita.py sync all`
- Apply: `python tools/casita.py sync all --apply`

The native Grocy 4.6 API resource inventory and implementation status are
tracked in [GROCY_4_6_API_RESOURCES.md](GROCY_4_6_API_RESOURCES.md).
