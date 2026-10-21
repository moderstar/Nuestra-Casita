# Milestone 19 Handoff

## Scope

This milestone adds optional, read-only Home Assistant entity state projection
to the existing Dashboard API and kitchen dashboard. There are no database,
container-topology, Grocy synchronization, or Home Assistant write changes.

## Bundle verification and import

After copying the bundle and checksum file to `/opt` on the Docker VM:

```bash
cd /opt
sha256sum -c nuestra-casita-home-assistant-milestone-19.bundle.sha256
git bundle verify /opt/nuestra-casita-home-assistant-milestone-19.bundle

cd /opt/Nuestra-Casita
git status --short
git switch development
git fetch /opt/nuestra-casita-home-assistant-milestone-19.bundle \
  feature/synchronization-framework:refs/remotes/canvas/milestone-19
git log --oneline --decorate development..refs/remotes/canvas/milestone-19
git merge --ff-only refs/remotes/canvas/milestone-19
```

Stop if the worktree is not clean, verification fails, or the merge is not a
fast-forward.

## Configure locally

Create a long-lived access token from the Home Assistant user profile and add
the following only to `/opt/Nuestra-Casita/.env`:

```dotenv
HOME_ASSISTANT_URL=http://192.168.8.157:8123
HOME_ASSISTANT_TOKEN=replace-with-the-real-token
HOME_ASSISTANT_ENTITY_IDS=sensor.example_temperature,binary_sensor.example_door
```

Replace the example IDs with exact, household-approved entities. Start with a
small non-sensitive list. Do not paste the token into Git or validation logs.

## Validate and deploy

```bash
cd /opt/Nuestra-Casita
PYTHONPATH=tools python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q tools tests

cd frontend
npm ci
npm test -- --run
npm run typecheck
npm run build
cd ..

docker compose config --services
docker compose build
docker compose up -d
docker compose ps
docker compose logs --tail=100 dashboard-api
```

Then browse to the existing LAN URL on port 8085:

1. Confirm all Grocy pages still load and chore completion still works.
2. Open Home Status and verify only allowlisted entities appear.
3. Verify units and `available`, `unavailable`, and `unknown` presentation.
4. Change one allowlisted entity in Home Assistant and use Refresh; confirm the
   new state appears.
5. Temporarily stop Home Assistant or use an invalid test URL, then confirm
   Home Status becomes limited while Grocy sections remain available.
6. Confirm there are no device controls, switches, sliders, or action buttons.
7. Restore valid configuration and confirm recovery.

Normal Home Status validation is read-only and does not modify Home Assistant.
Do not push to GitHub until this live review succeeds.

## Canvas validation results

- Backend: 173 tests passed, including mocked authentication, timeout,
  connection, malformed response, allowlist, availability, composition, API,
  and dashboard-isolation cases.
- Frontend: 14 tests passed; TypeScript and the production Vite build passed.
- Python compilation and dependency-boundary checks passed.
- The Home Assistant transport was statically verified to contain only reads.
- CLI help remained byte-identical to the `c095cec` base, and Grocy resource,
  payload, registry, and synchronization sources were unchanged.
- Static Compose validation confirmed the existing two services and port 8085.
- `git diff --check` passed.
- Docker and the live Home Assistant instance were unavailable in Canvas, so
  container and live-LAN validation remain required on the Docker VM.
- No live Home Assistant or Grocy requests were made.

The SHA-256 checksum is delivered beside the bundle in
`nuestra-casita-home-assistant-milestone-19.bundle.sha256`.

## Rollback

Stop the containers, return through the site's approved Git workflow to
`c095cec5207330d8d86af7690520218820158f73`, rebuild, and restart Compose.
There is no data migration or Home Assistant state change to reverse. Remove
the three optional Home Assistant environment variables if the integration
should remain disabled.
