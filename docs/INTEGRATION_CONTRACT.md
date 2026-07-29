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

Expected capabilities:

- Devices
- Notifications
- Selected household state

Entity IDs, service calls, areas, and device registries stay inside the
adapter.

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

## Future Integration Registry

The current registry is Grocy-resource-specific and remains unchanged.

A future platform registry will manage adapter instances, capability
ownership, and household configuration. It should be implemented when the
second real integration is added so its API is based on demonstrated needs
rather than assumptions.
