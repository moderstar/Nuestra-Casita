# Dashboard API

The read-only FastAPI transport uses existing application services; routes
never call Grocy directly.

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | None | Process liveness only |
| POST/DELETE | `/api/v1/session` | Password/cookie | Start or end a session |
| GET | `/api/v1/dashboard` | Cookie | Complete snapshot |
| GET | `/api/v1/inventory` | Cookie | Inventory |
| GET | `/api/v1/shopping-lists` | Cookie | Shopping Lists |
| GET | `/api/v1/recipes` | Cookie | Recipes |
| GET | `/api/v1/chores` | Cookie | Chores |
| GET | `/api/v1/meal-plan` | Cookie | Meal Plan |
| GET | `/api/v1/tasks` | Cookie | Tasks |

Responses use `{"version":"1","state":"available","data":[],"errors":[]}`.
State is `available`, `empty`, or `degraded`. Errors expose only a safe code,
source, capability, and generic message. Decimal values are strings and dates
and datetimes are ISO 8601. Opaque domain IDs replace Grocy database IDs.

## Authentication and security

```bash
curl -i -c cookies.txt -H 'Content-Type: application/json' \
  -d '{"password":"household-password"}' \
  https://casita.lan/api/v1/session
curl -b cookies.txt https://casita.lan/api/v1/dashboard
```

The password uses constant-time comparison. Login creates a signed, expiring,
`HttpOnly`, `SameSite=Strict` cookie. The browser never receives the password,
signing secret, or Grocy key. Secure cookies default on, so production requires
private HTTPS. There is no authentication bypass. CORS is off unless explicit
origins are configured, and wildcard origins are rejected.

All household routes are GET-only. Shopping mutations, Task completion, and
other destructive operations are absent. One integration failure degrades its
section without preventing unrelated data from loading.
