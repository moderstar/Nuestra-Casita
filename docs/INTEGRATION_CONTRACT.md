# Integration Contract

## Goal

An integration connects one external system to Nuestra Casita without leaking
that system's API into the domain or dashboard.

The code contract lives in `casita.integrations`.

## Required Interface

Every adapter provides:

- `descriptor`: stable key, display name, version, and capabilities
- `health()`: current connectivity and degradation information
- `read(request)`: normalized domain records grouped by capability

The common capabilities are:

- Household
- People
- Shopping
- Inventory
- Recipes
- Chores
- Calendar
- Budget
- Notifications
- Devices
- Media

Capability declarations allow the application layer to choose an adapter
without testing concrete classes or vendor names.

## Optional Synchronization Interface

Only integrations with declarative resources need synchronization.

`SynchronizingIntegration` adds:

- `plan(request)`: create a backend-neutral dry-run plan
- `apply(plan)`: apply a previously generated plan and return counts

The integration remains responsible for backend payloads and IDs. The shared
plan contract carries only identities, display names, actions, and field
differences.

Delete operations are not in the initial contract because the current Grocy
engine intentionally supports create, update, and match only. Deletion should
be added after project-wide ownership and safety rules are designed.

`DiagnosableIntegration` supplies actionable adapter-owned checks.
`RuntimeInspectableIntegration` supplies normalized integration version,
database description, aggregate metrics, connectivity, and errors for
dashboard presentation. Neither contract permits raw vendor responses to
cross the adapter boundary.

## Optional Activity Interfaces

Interactive household activity uses capability-specific contracts rather than
a generic object API. `ShoppingMutationIntegration` supports bounded product
search, add, purchased-state, and exact removal commands.
`ChoreMutationIntegration` supports user discovery, definition creation and
editing, safe deactivation, and completion.
Commands contain opaque domain IDs and decimal-safe quantities; adapters alone
resolve native IDs and payloads. Each operation writes through one configured
capability owner and immediately reads authoritative state back.

Shopping items remain live Grocy activity. Chore definitions and history are
Grocy-owned operational data. Chore deletion, stock booking, bulk removal, and
arbitrary mutation are excluded.

## Planned Adapters

### Grocy

Expected capabilities:

- Shopping
- Inventory
- Recipes
- Chores

The existing Grocy synchronization packages remain operational. A future
adapter should compose those packages rather than rewrite their payload,
resource, comparison, and apply logic.

### Home Assistant

Implemented capability:

- Devices

The adapter reads only explicitly allowlisted entity states and maps them to
`Device`. Native state values, units, entity domains, availability, and a
small safe set of scalar display attributes are normalized at the boundary.
Opaque domain IDs prevent native entity IDs from becoming application
identity; `SourceReference` retains traceability. Service calls, controls,
areas, registries, and event subscriptions are not implemented.

### Nextcloud

Expected capabilities:

- People
- Calendar
- Tasks or notifications where appropriate

CalDAV, CardDAV, Nextcloud IDs, and application passwords stay inside the
adapter.

### Actual Budget

Expected capabilities:

- Budget

Account IDs, category IDs, schedules, and transaction schemas stay inside the
adapter. The initial dashboard projection should be read-only.

### Immich

Expected capabilities:

- Media

Asset IDs, thumbnails, albums, and signed media URLs stay inside the adapter.

## Mapping Rules

- Domain IDs are stable within Nuestra Casita and need not equal backend IDs.
- `SourceReference` preserves the adapter key, external ID, and external type.
- Datetimes must be timezone-aware before entering cross-integration flows.
- Currency values use `Decimal` through the `Money` model.
- Adapters return immutable domain records.
- Empty or unavailable sections are valid; adapters report health separately.
- Runtime data may be projected for reading but must not be treated as
  declarative synchronization input.

## Error and Freshness Rules

- A failed backend must not prevent unrelated capabilities from loading.
- Health and data freshness are separate: cached data may remain usable while
  an integration is unavailable.
- Adapters should return the time each capability was refreshed.
- Application orchestration decides whether stale data is displayed.
- Dashboard clients receive stale-section metadata, not backend exceptions.

## Integration Registration

`IntegrationDirectory` now coordinates Grocy and the optional Home Assistant
adapter by declared capability and explicit ownership. Backend replacement
continues to use `BackendRegistry`; adding a read-only secondary integration
does not require another registry or synchronization engine.
