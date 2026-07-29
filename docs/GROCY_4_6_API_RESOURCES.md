# Grocy 4.6 API Resource Inventory

This inventory tracks the native entities exposed through Grocy 4.6's
generic `/objects/{entity}` API and Nuestra Casita's synchronization status.
It is based on the `ExposedEntity` schema in Grocy's tagged
`v4.6.0` OpenAPI specification.

Status meanings:

- **Implemented**: Registered in Nuestra Casita and included in `sync all`.
- **Planned**: A native Grocy resource that may be synchronized in a future
  milestone.
- **Not Applicable**: Runtime, derived, security, journal, or internal data
  that should not be managed from an authoritative synchronization catalog.

| Grocy entity | Status | Notes |
| --- | --- | --- |
| `products` | Implemented | Product master data |
| `chores` | Implemented | Recurring chore definitions; execution state is excluded |
| `product_barcodes` | Planned | Product barcode mappings |
| `batteries` | Implemented | Battery definitions; charge history is excluded |
| `locations` | Implemented | Stock locations |
| `quantity_units` | Implemented | Quantity unit master data |
| `quantity_unit_conversions` | Planned | Quantity unit conversion rules |
| `shopping_list` | Not Applicable | Runtime shopping-list items |
| `shopping_lists` | Planned | Named shopping lists |
| `shopping_locations` | Implemented | Shopping stores and locations |
| `recipes` | Implemented | Declarative Recipe definitions; ingredients and runtime serving state are excluded |
| `recipes_pos` | Implemented | Declarative Recipe ingredients; fulfillment and calculated state are excluded |
| `recipes_nestings` | Planned | Nested recipe relationships |
| `tasks` | Planned | Household task definitions |
| `task_categories` | Implemented | Task category master data |
| `product_groups` | Implemented | Product group master data |
| `equipment` | Planned | Equipment master data |
| `api_keys` | Not Applicable | Security credentials |
| `userfields` | Planned | Custom field definitions |
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
