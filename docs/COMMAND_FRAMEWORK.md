# Dashboard and Command Framework

## Purpose

The command framework is Nuestra Casita's first cohesive application entry
point. It presents household commands while preserving the platform dependency
direction:

```text
CLI
→ Composition Root
→ Application Services
→ Integration Contracts
→ Grocy Adapter
```

The CLI parses arguments and renders results. It does not load Grocy endpoints,
call the synchronization engine, validate catalogs, or assemble dashboard
data.

## Commands

The unified entry point is `python tools/casita.py`, presented as `casita` in
usage output.

| Command | Application service | Result |
| --- | --- | --- |
| `casita dashboard` | `DashboardService` | Platform, integration, inventory, and health summary |
| `casita doctor` | `DoctorService` | Ordered actionable diagnostic checks |
| `casita sync [resource]` | `SynchronizationApplicationService` | Structured dry-run synchronization plan |
| `casita sync [resource] --apply` | `SynchronizationApplicationService` | Structured explicit apply workflow |
| `casita inventory` | `InventoryService` | Backend-neutral inventory items |
| `casita recipes` | `RecipeService` | Backend-neutral Recipe definitions |

`casita sync` defaults to `all`. Every existing individual resource remains
available, including `casita sync products` and
`casita sync product-groups --apply`.

Legacy lookup, validation, and export commands remain available through
`MaintenanceService`. The CLI does not invoke their Grocy implementation
directly.

## Application Services

`SynchronizationApplicationService` coordinates `SynchronizationPlanner` and
`SynchronizationExecutor` through `CatalogApplicationService`. The catalog
service validates each resource command and returns a structured
`CatalogOperationResult`. The planner and executor resolve the explicitly
configured owner through `IntegrationDirectory` and invoke the
`SynchronizingIntegration` contract. The production Grocy adapter translates
native plans and results into structured contracts while preserving resource
order, payload builders, comparisons, plan formatting, and apply behavior.

`DoctorService` owns platform diagnostics. Local checks validate:

- Configuration
- Required project directories
- Catalog files for every registered resource
- Resource registration and synchronization order
- Payload and comparison callables

Adapter-owned diagnostics validate:

- Grocy connectivity
- API authentication
- Adapter connectivity

Failures carry actionable messages and cause the doctor command to exit with
status `1`. A completely passing report exits with status `0`.

`DashboardService.overview()` augments the existing `DashboardSnapshot` with
backend-neutral `IntegrationRuntime` values. The Grocy adapter owns retrieval
and normalization of its version, database engine, Product count, Recipe
count, and Location count.

## Configuration

The composition root loads configuration in this order:

1. An explicitly supplied configuration path
2. `.env` at the repository root
3. `/opt/Nuestra-Casita/.env`
4. Existing process environment values

Required values:

```text
GROCY_URL
GROCY_API_KEY
```

Optional values:

```text
CASITA_TIMEZONE=UTC
CASITA_HOUSEHOLD_ID=default
CASITA_HOUSEHOLD_NAME=Nuestra Casita
```

All concrete construction occurs in `casita.bootstrap`. One
`GrocyApiClient` is shared by the Grocy read adapter and the established
synchronization transport.

## Dependency Rules

- `tools/casita.py` imports application construction and backend-neutral
  domain contracts, never a Grocy client or sync engine.
- Application services import integration contracts, never Grocy packages.
- The Grocy adapter may compose Grocy transports and workflows.
- Only the composition root constructs concrete clients and assigns
  capability or synchronization ownership.
- Dashboard models contain normalized integration status and domain records,
  never native Grocy responses or identifiers.

## Current Limitations

- Last synchronization is displayed as `Not recorded`. Persistence is outside
  this milestone, and an in-memory timestamp would not survive a CLI process.
- Dashboard reads are synchronous and uncached.
- The CLI is currently invoked through `python tools/casita.py`; packaging a
  console-script executable can be added with the future deployment milestone.
