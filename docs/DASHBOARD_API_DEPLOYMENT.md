# Dashboard API Docker Deployment

Copy `.env.dashboard.example` to `.env`, replace example credentials, and use
a random session secret of at least 32 characters. Existing Grocy and household
variable names remain unchanged.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CASITA_API_BIND_ADDRESS` | `127.0.0.1` | Docker host bind address |
| `CASITA_API_PORT` | `8080` | Published port |
| `CASITA_API_PASSWORD` | required | Household password, 12+ characters |
| `CASITA_API_SESSION_SECRET` | required | Cookie secret, 32+ characters |
| `CASITA_API_SESSION_TTL_SECONDS` | `86400` | Session lifetime |
| `CASITA_API_COOKIE_SECURE` | `1` | HTTPS-only cookie |
| `CASITA_REQUEST_TIMEOUT_SECONDS` | `10` | Grocy request timeout |
| `CASITA_API_ALLOWED_ORIGINS` | blank | Explicit UI origins |

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose logs dashboard-api
docker compose down
```

The container runs as UID 10001 with a read-only filesystem, tmpfs `/tmp`,
`no-new-privileges`, a liveness health check, and `unless-stopped` restart.
No volume, database, Redis, or broker is required. Compose binds loopback by
default; deliberately choose a private LAN address or private HTTPS reverse
proxy. Public exposure is out of scope.
