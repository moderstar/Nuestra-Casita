# Milestone 18 Handoff

## Scope

Grocy 4.6 is authoritative for chore definitions and activity. The kitchen
dashboard now supports chore create, edit, completion, activation, and safe
deactivation. No database, container, credential, or production environment
change is required.

Deletion is deliberately unavailable. In Grocy 4.6, deleting a Chore cascades
to its execution log; use deactivation to retain household history. Validate
against the live instance with a household-approved disposable chore only.

## Bundle verification and import

Run these commands on the Docker host after copying the bundle to `/opt`:

```bash
cd /opt
sha256sum -c nuestra-casita-grocy-native-chores-milestone-18.bundle.sha256
git bundle verify /opt/nuestra-casita-grocy-native-chores-milestone-18.bundle

cd /opt/Nuestra-Casita
git status --short
git fetch /opt/nuestra-casita-grocy-native-chores-milestone-18.bundle \
  feature/synchronization-framework:refs/remotes/canvas/milestone-18
git log --oneline --decorate development..refs/remotes/canvas/milestone-18
git merge --ff-only refs/remotes/canvas/milestone-18
```

Do not continue if the worktree is not clean, bundle verification fails, or
the fast-forward is not possible.

## Local validation

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q tools tests
cd frontend
npm test -- --run
npm run typecheck
npm run build
cd ..
docker compose config --services
docker compose build
docker compose up -d
docker compose ps
```

Confirm that the services remain `dashboard-api` and `kitchen-dashboard`, and
that the dashboard is reachable through the existing LAN port 8085 routing.

## Live Grocy validation

1. Sign in and confirm existing chores and inactive definitions appear.
2. Confirm a change made directly in Grocy appears after Refresh.
3. Create a disposable manual chore in the dashboard and verify it in Grocy.
4. Edit its description and assignment; verify Grocy's next assignment.
5. Complete it once and confirm the execution appears in Grocy history.
6. Confirm its start date is locked, then deactivate it from the dashboard.
7. Verify the execution history remains present.
8. Run `python tools/casita.py sync chores` and confirm the resource is
   rejected; dry-run `sync all` and confirm unrelated resources still plan.

Do not delete a real Chore or run an apply operation merely for validation.
Do not push to GitHub until the live review succeeds.

## Canvas validation results

- Backend: 158 tests passed.
- Frontend: 11 tests passed; TypeScript check and production Vite build passed.
- Python compilation and dependency-boundary checks passed.
- Preserved CLI help surfaces were byte-identical to the Milestone 17 base;
  the only intentional sync surface change is removal of `chores`.
- Static Compose validation confirmed the existing two services and port 8085.
- `git diff --check` passed.
- Docker was not installed in Canvas, so image build, rendered Compose
  validation, and live Grocy verification are deferred to the Docker host.
- No live Grocy writes were performed.

The SHA-256 checksum is delivered beside the bundle in
`nuestra-casita-grocy-native-chores-milestone-18.bundle.sha256`.

## Rollback

Stop the containers, fast-forward or reset only through the site's approved
Git workflow to commit `e4107ad61f8f597778da47a9658a88e2c7189d07`, rebuild,
and restart Compose. There is no Nuestra Casita data migration to reverse.
Chore changes already committed to Grocy remain Grocy-owned and are not undone
by an application rollback.
