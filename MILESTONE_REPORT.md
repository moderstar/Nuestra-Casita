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
