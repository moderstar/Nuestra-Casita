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

Products retain the backward-compatible `sync_products()` entry point while
using the same generic synchronization and apply engines as Product Groups
and the other registered resources.

## Complete Synchronization

The `sync all` command runs registered resources in dependency-aware order:

1. Product Groups
2. Quantity Units
3. Locations
4. Products

The order is defined by `SYNC_RESOURCE_ORDER` in `casita.registry`, not by the
CLI. The orchestration workflow invokes the same synchronization function used
by each individual resource command.

- Dry run: `python tools/casita.py sync all`
- Apply: `python tools/casita.py sync all --apply`
