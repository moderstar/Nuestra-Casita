# Milestone 17 Report: Interactive Grocy Activity

## Summary

Milestone 17 adds safe everyday Shopping List and chore interactions to the
kitchen dashboard without changing the backend-neutral structure. Application
services expose narrow mutation contracts, Grocy resolves opaque IDs, and each
successful write is followed by an authoritative read.

Shopping supports product search, free-text items, decimal quantities,
multiple lists, purchased/unpurchased state, and confirmed exact removal.
Chores support completion through Grocy's execution operation. Chore creation
is deferred because definitions are Git-authoritative in `catalog/chores.csv`.

## Safety

- Signed sessions and double-submit CSRF validation protect every write.
- Required idempotency keys prevent duplicate retries within the API process.
- Bounded request models and application validation reject invalid input.
- Opaque domain IDs are resolved against fresh backend collections.
- Unexpected Grocy errors receive safe HTTP responses.
- Shopping completion never books stock.
- No generic proxy, bulk delete, live chore creation, Task operation, or schema
  migration was added.

## Compatibility

Grocy 4.6 generic `shopping_list` object endpoints avoid the specialized
endpoint's decimal truncation defect fixed in 4.7. Chore completion uses
`/chores/{id}/execute`. Existing CLI commands and the two-container deployment
topology remain unchanged.

## Validation

Automated validation is fully mocked and performs no live Grocy writes:

- Python: 146 tests passed; `compileall` passed.
- Frontend: 9 tests passed; TypeScript and production Vite build passed.
- Dependency boundary: application/domain packages contain no Grocy imports.
- CLI: eight existing command/help surfaces were byte-identical to Milestone 16.
- Deployment: static Compose validation confirmed two services, private API,
  and frontend port 8085. The Docker executable was unavailable for a live
  Compose render or launch.
- Whitespace: `git diff --check` passed.
