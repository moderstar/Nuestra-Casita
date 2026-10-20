# Dashboard API Docker Deployment

Copy `.env.dashboard.example` to `.env`, replace example credentials, and use
a random session secret of at least 32 characters. Existing Grocy and household
variable names remain unchanged.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CASITA_API_PASSWORD` | required | Household password, 12+ characters |
| `CASITA_API_SESSION_SECRET` | required | Cookie secret, 32+ characters |
| `CASITA_API_SESSION_TTL_SECONDS` | `86400` | Session lifetime |
| `CASITA_API_COOKIE_SECURE` | `1` | HTTPS-only cookie |
| `CASITA_REQUEST_TIMEOUT_SECONDS` | `10` | Grocy request timeout |
| `CASITA_API_ALLOWED_ORIGINS` | blank | Explicit UI origins |
| `CASITA_FRONTEND_BIND_ADDRESS` | `127.0.0.1` | Frontend host bind address |
| `CASITA_FRONTEND_PORT` | `8085` | Frontend published port |

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose logs dashboard-api
docker compose logs kitchen-dashboard
docker compose down
```

For a no-write smoke test, sign in, inspect every page, use Refresh, and verify
that the Shopping and Chores controls render. Automated tests use mocked Grocy
responses and never modify household data. Test live writes only with
household-approved disposable shopping data and a due chore.

Rollback is a normal Git/container rollback: stop the services, check out the
prior known-good commit (`82f08db94460c05b17e3315443f0bb929943d7dd` for
Milestone 16), rebuild, and start Compose. No migration, volume, or persistent
dashboard state needs reversal. Activity already confirmed by Grocy remains
Grocy-owned and is not undone automatically.

The API is exposed only to the Compose network. The separate frontend service
publishes host port `8085` by default and proxies `/api/` to
`dashboard-api:8080`; the browser therefore uses one origin and the existing
session cookie without CORS. Both containers use read-only filesystems,
temporary writable runtime paths, `no-new-privileges`, health checks, and
`unless-stopped` restart. No volume, database, Redis, or broker is required.

Compose binds the frontend to loopback by default. For intentional LAN access,
set `CASITA_FRONTEND_BIND_ADDRESS` to the Docker VM's LAN IP (preferred) or
`0.0.0.0`, then browse to `http://VM-IP:8085`. Plain HTTP requires
`CASITA_API_COOKIE_SECURE=0`. Restore `CASITA_API_COOKIE_SECURE=1` when serving
the same origin through private HTTPS. Public exposure and Cloudflare tunnels
are out of scope.
