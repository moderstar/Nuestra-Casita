# Milestone 18 Report: Grocy-Native Chore Management

## Summary

Milestone 18 makes Grocy 4.6 the sole authority for chore definitions,
schedules, assignments, active state, and execution history. The authenticated
kitchen dashboard can create, edit, complete, activate, and deactivate chores
through backend-neutral application contracts and the existing Grocy adapter.

The legacy header-only chore catalog and synchronization resource are removed.
`sync chores` is rejected and `sync all` no longer contains a chore stage, so
CLI synchronization cannot overwrite live Grocy chores. All unrelated catalog
resources retain their established behavior.

## Safety and Compatibility

- Every dashboard write retains signed-session, CSRF, validation, and
  idempotency protection.
- Browser clients see opaque chore and user identifiers; Grocy credentials and
  native IDs stay server-side.
- Daily, weekly, monthly, manual, hourly, yearly, and adaptive schedules map to
  Grocy 4.6 native fields.
- Native assignment modes use the current `/users` collection and trigger
  Grocy's next-assignment recalculation after create or edit.
- A start date becomes immutable in the dashboard when execution history
  exists, matching Grocy's own form behavior.
- Deletion is intentionally unavailable because Grocy 4.6 cascades Chore
  deletion to `chores_log`; deactivation preserves all history.
- Chore completion continues to use `/chores/{id}/execute`.
- UUID fallback behavior remains compatible with plain HTTP on a private LAN.

## Validation

Automated validation uses mocked Grocy responses and performs no live writes.
Final test counts, CLI comparisons, dependency checks, bundle identity, and
checksum are recorded in the Milestone 18 handoff document.
