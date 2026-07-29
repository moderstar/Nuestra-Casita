# Nuestra Casita Architecture

Nuestra Casita uses registered resource definitions to synchronize
version-controlled catalogs with Grocy.

The synchronization flow is:

1. Load a resource definition from `casita.registry`.
2. Load its CSV catalog and Grocy endpoint through `casita.sync_engine`.
3. Match objects by normalized name and build a create, update, or match plan.
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

Products retain the backward-compatible `sync_products()` entry point while
using the same generic synchronization and apply engines as Product Groups
and the other registered resources.

## Complete Synchronization

The `sync all` command runs registered resources in dependency-aware order:

1. Product Groups
2. Quantity Units
3. Locations
4. Shopping Locations
5. Products
6. Task Categories
7. Chores

The order is defined by `SYNC_RESOURCE_ORDER` in `casita.registry`, not by the
CLI. The orchestration workflow invokes the same synchronization function used
by each individual resource command.

- Dry run: `python tools/casita.py sync all`
- Apply: `python tools/casita.py sync all --apply`

The native Grocy 4.6 API resource inventory and implementation status are
tracked in [GROCY_4_6_API_RESOURCES.md](GROCY_4_6_API_RESOURCES.md).
