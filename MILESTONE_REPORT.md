# Milestone 19 Report: Home Assistant Read-Only Integration

## Summary

Milestone 19 adds the first Home Assistant integration through the existing
backend-neutral Devices capability. An optional authenticated REST adapter
reads current state for explicitly allowlisted entities and maps them into
`Device` records. The kitchen dashboard adds a touch-friendly Home Status page
and a compact overview card.

Grocy synchronization and interactive household activity are unchanged. Home
Assistant remains authoritative, and normal operation requires only local
network access.

## Live validation follow-up

The post-deployment follow-up adds independent, non-overlapping browser polls:
the aggregate dashboard refreshes every 30 seconds and the read-only Home
Assistant device endpoint refreshes every 10 seconds. Polling pauses while the
document is hidden and both sources refresh when it becomes visible. Ordered
merging and abort cleanup preserve valid data through delayed or failed
requests without remounting active forms.

Dashboard navigation now uses stable same-origin paths and the native History
API. Direct URLs, reloads, and browser Back/Forward retain the selected page;
unknown routes fall back to Overview. This introduces no routing dependency,
backend endpoint, credential exposure, or Home Assistant write capability.

Follow-up validation completed with 173 backend tests and 26 frontend tests.
Python compilation, dependency-boundary coverage, TypeScript validation, the
production Vite build, and whitespace checks pass. No backend, Grocy adapter,
synchronization, Compose, Nginx, or environment configuration file changed.

## Security and failure isolation

- The long-lived access token is loaded only from process configuration.
- Browser responses never contain the token or Authorization header.
- An empty allowlist exposes no entities; non-allowlisted entities are never
  projected.
- Only `GET /api/` and `GET /api/states` are implemented by the integration
  client. No state writes, service calls, automations, or controls exist.
- Requests use the configured timeout, validated between 0.1 and 60 seconds.
- Authentication, connection, timeout, status, JSON, and schema failures are
  converted into a degraded Home dashboard section without breaking Grocy
  sections or exposing upstream details.
- Available, unavailable, unknown, and missing allowlisted states remain
  distinct.

## Validation

All automated Home Assistant tests use mocked responses and perform no live
network calls. Final test counts, dependency validation, CLI regression,
bundle identity, and checksum are recorded in the Milestone 19 handoff.
