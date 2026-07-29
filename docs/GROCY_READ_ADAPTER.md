# Grocy Read Adapter

## Purpose

`casita.integrations.grocy` is the production read boundary between Grocy 4.6
and Nuestra Casita. It reads native Grocy API responses and returns only
backend-neutral domain models through the common `Integration` contract.

Raw Grocy dictionaries, endpoint vocabulary, and database identifiers remain
inside the adapter package.

## Supported Capabilities

| Capability | Grocy 4.6 sources | Domain output |
| --- | --- | --- |
| Inventory | `/stock`, Quantity Units | `Inventory` and `InventoryItem` |
| Shopping | Shopping Lists, Shopping List Items, Products, Quantity Units | `ShoppingList` and `ShoppingItem` |
| Recipes | Recipes, Recipe Positions, Products, Quantity Units | `Recipe` and `RecipeIngredient` |
| Chores | `/chores`, Chore definitions | `Chore` |

The adapter requests only the endpoints needed for each requested capability.
It validates that list endpoints return dictionaries before translation.

## Translation Boundary

Mapping functions live in `casita.integrations.grocy.mapping`. They are pure
translations and make no network requests.

Native numeric values are converted through `Decimal`. Grocy's local
timestamps are interpreted using the adapter's configured timezone and
normalized to UTC. The `2999` date used by Grocy for an unscheduled Chore or
no expiration is mapped to `None`.

Grocy integer identifiers are never assigned directly to domain models.
Stable UUID identities are derived inside the adapter from the resource type
and native identifier. Domain source references are intentionally omitted so
raw Grocy identifiers do not cross the integration boundary.

## Mapping Decisions

### Inventory

`/stock` is Grocy's supported current-stock projection. Aggregated amounts are
used for products with subproducts; otherwise the direct amount is used.
Quantity Unit names come from the shared Quantity Unit lookup.

The current stock endpoint aggregates locations, so the adapter does not
misrepresent a Product's default Location as its actual stock Location.
Per-location inventory can be added later using native stock-location
endpoints when the domain contract supports multiple locations per Product.

### Shopping

Named Shopping Lists contain their current Shopping List Items. Product-backed
items use the Product name; note-only entries use the note as their display
name. Completion state, amount, Quantity Unit, note, and latest known
timestamp are normalized.

### Recipes

Only native normal Recipes are returned. Recipe Positions become declarative
ingredients by resolving Product and Quantity Unit names. Fulfillment,
shopping-list state, costs, and stock calculations remain excluded.

### Chores

Chore definitions provide name and description. `/chores` provides current
due and assignment state. The adapter does not expose Chore execution logs.
The domain `completed` value remains false because the native current Chore
projection represents the next occurrence rather than a completed instance.

### Tasks

Grocy Tasks are not translated into Notifications. A Task is not inherently a
notification, and the current domain has no Household Task model. A future
Task capability should add the correct backend-neutral concept instead of
forcing a lossy mapping.

## Shared Components

The read adapter and synchronization engine share:

- `GrocyApiClient` authenticated transport
- Native resource endpoints already established by resource definitions
- Product, Recipe, and Quantity Unit lookup concepts
- Decimal and identity normalization principles

Synchronization remains declarative and catalog-driven. Reading remains
runtime projection-driven. They are independently testable and do not invoke
one another.

## Adapter Guidelines

Future adapters should:

1. Implement the common `Integration` contract.
2. Keep vendor clients and response records inside their adapter package.
3. Translate explicitly into domain models.
4. Use stable opaque domain identities.
5. Declare only capabilities they fully support.
6. Keep writes and synchronization behind separate optional contracts.
7. Register explicitly through the composition root.

No vendor-specific branch belongs in an application service or dashboard
assembler.

## Current Limitations

- Reads are full capability snapshots; Grocy 4.6 does not provide a common
  incremental cursor for these resources.
- There is no application cache yet, so separate dashboard capability reads
  can repeat Product and Quantity Unit requests.
- Inventory is aggregated by Product and does not expose multiple physical
  stock locations.
- Chore assignees use stable person identities, but Person profile reads are
  not yet a supported Grocy capability.
- Nested Recipes are not expanded.
