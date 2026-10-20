# Milestone 17 Handoff — Interactive Grocy Activity

## Scope

- Add product or free-text shopping items with decimal quantity and list choice.
- Mark an item purchased without booking stock, reopen it, or remove it after
  confirmation.
- Complete an existing chore through Grocy's execution endpoint.
- Refresh authoritative Grocy-backed state after every confirmed operation.
- Preserve Git ownership of chore definitions; dashboard creation is deferred.

## Deployment

1. Verify the imported branch includes the Milestone 17 commit and bundle.
2. Keep the existing dashboard variables and two-service Compose topology.
3. Run `docker compose build` and `docker compose up -d`.
4. Check `docker compose ps`, both logs, and `/api/v1/health` through port 8085.
5. Sign in on the iPad and validate navigation and refresh before performing
   any explicitly authorized live activity test.

No schema migration, cache, database, volume, or new public port is introduced.

## Rollback

Stop Compose, check out Milestone 16 commit
`82f08db94460c05b17e3315443f0bb929943d7dd`, rebuild, and restart. Confirmed
Grocy activity is not reverted by application rollback. Remove disposable test
items manually only when household authorization permits it.
