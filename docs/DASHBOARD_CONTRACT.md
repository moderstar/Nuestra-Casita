# Kitchen Dashboard Contract

## Boundary

The future kitchen dashboard consumes only Nuestra Casita domain models
assembled into `DashboardSnapshot`.

It must never:

- Call Grocy, Home Assistant, Nextcloud, Actual Budget, or Immich directly
- Depend on vendor entity names or IDs
- Store integration credentials
- Interpret backend-specific failure responses

No dashboard or frontend is implemented in this milestone.

## Version

The initial internal contract version is `1`. Contract versions allow a future
API or local application service to evolve independently from dashboard
deployments.

## Sections

| Section | Expected data | Capability owner | Fresh target | Stale allowance |
| --- | --- | --- | --- | --- |
| Today | Current and upcoming calendar events | Calendar integration | 5 minutes | 1 hour |
| Shopping | Named lists and checked/unchecked items | Shopping integration | 30 seconds | 5 minutes |
| Inventory | Stock, location, expiration, low-stock state | Inventory integration | 5 minutes | 30 minutes |
| Meals | Recipes and future meal-plan projection | Recipe integration | 5 minutes | 1 hour |
| Chores | Due state, assignment, and completion projection | Chore integration | 1 minute | 10 minutes |
| Budget | Period income, spending, and available amount | Budget integration | 15 minutes | 2 hours |
| Home | Device availability and normalized state | Device integration | 10 seconds | 1 minute |
| Media | Curated household media | Media integration | 1 hour | 24 hours |
| Notifications | Normalized household alerts | Platform/integrations | 30 seconds | 5 minutes |

The refresh values are initial policies, not polling requirements. Push events
or webhooks may refresh a section sooner.

## Ownership

- Integrations own retrieval and translation from their backends.
- Household configuration will select one primary owner per capability.
- Nuestra Casita owns aggregation, refresh scheduling, cache decisions, and
  contract versioning.
- The dashboard owns rendering and local interaction state only.

If multiple integrations provide one capability, the application layer must
resolve ownership before constructing a snapshot. The dashboard does not merge
vendor records.

## Cache Expectations

- Cache data by household and capability.
- Track `refreshed_at` independently for each capability.
- Serve stale data within the section's stale allowance when refresh fails.
- Mark stale sections in `DashboardSnapshot.stale_sections`.
- Never replace usable cached data with an error payload.
- Do not persist credentials or raw vendor responses in a dashboard cache.
- Device controls and other future writes must bypass stale read projections
  and use explicit commands.

No cache implementation is selected in this milestone.

`casita.application.DashboardService` now performs in-memory snapshot
assembly. It marks sections stale when an integration read fails; a future
cache service will decide whether previously known records can also be served.

## Snapshot Contents

`DashboardSnapshot` includes:

- Contract version and generation timestamp
- Household
- Today's calendar events
- Shopping lists
- Inventory projection
- Recipes
- Chores
- Budget summary
- Devices
- Media
- Notifications
- Sections currently served from stale data

All contents use models from `casita.domain`.

The terminal dashboard wraps the snapshot in the backend-neutral `Dashboard`
contract. It adds normalized integration connectivity, version, database
description, aggregate resource counts, configuration state, missing
resources, synchronization timestamp, and errors. Concrete adapters retrieve
and translate this metadata; presentation code never reads vendor endpoints.

Last synchronization currently reports `Not recorded`. Persisting this value
is intentionally deferred with the broader platform persistence decision.

## Refresh Strategy

1. The application layer checks cached capability data.
2. Fresh data is used immediately.
3. Stale-but-allowed data is returned while a background refresh starts.
4. Missing or expired data triggers a synchronous refresh when practical.
5. Failed sections are omitted or marked stale without blocking other
   sections.
6. A new immutable snapshot is assembled after refreshed data arrives.

The current application layer implements direct reads and snapshot assembly.
Cache lookup, background refresh, and push-triggered refresh remain deferred.

## Future Expansion

New sections may be introduced by:

1. Adding or extending a genuine household domain model.
2. Adding a capability when no existing capability fits.
3. Mapping one or more integrations to that capability.
4. Adding a section contract and refresh policy.
5. Versioning the dashboard contract if the snapshot shape changes.

Likely future sections include household documents, energy use, deliveries,
vehicles, guest mode, maintenance, and emergency information.
