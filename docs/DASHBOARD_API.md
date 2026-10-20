# Dashboard API

The FastAPI transport uses existing application services; routes never call
Grocy directly. Interactive writes use narrow shopping and chore contracts.

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
| GET | `/api/v1/shopping-products?query=` | Cookie | Bounded product choices |
| POST | `/api/v1/shopping-lists/{list}/items` | Cookie + CSRF | Add product or note |
| PUT | `/api/v1/shopping-lists/{list}/items/{item}` | Cookie + CSRF | Set purchased marker |
| DELETE | `/api/v1/shopping-lists/{list}/items/{item}` | Cookie + CSRF | Remove exact item |
| POST | `/api/v1/chores/{chore}/complete` | Cookie + CSRF | Record chore completion |
| GET | `/api/v1/chore-users` | Cookie | Native Grocy assignment choices |
| POST | `/api/v1/chores` | Cookie + CSRF | Create a chore definition |
| PUT | `/api/v1/chores/{chore}` | Cookie + CSRF | Edit or reactivate a chore |
| POST | `/api/v1/chores/{chore}/deactivate` | Cookie + CSRF | Preserve history and deactivate |

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
`HttpOnly`, `SameSite=Strict` cookie. Login also creates a signed, expiring
CSRF cookie. Every state-changing request echoes it in `X-CSRF-Token`; each
activity mutation also carries an 8–128 character `Idempotency-Key`, so a
duplicate retry does not repeat the backend write. The browser never receives the password,
signing secret, or Grocy key. Secure cookies default on, so production requires
private HTTPS. There is no authentication bypass. CORS is off unless explicit
origins are configured, and wildcard origins are rejected.

Bounded request models validate lengths and decimal quantities. Opaque IDs are
resolved against current backend state. Missing records and conflicts receive
safe explicit responses, while unexpected upstream details remain private.
Task completion and generic object proxying are absent. One integration
failure still degrades its section without blocking unrelated data.

Chore definitions are Grocy-owned. Creation and editing support native period
and assignment modes and recalculate the next assignment after a successful
write. Grocy 4.6 deletes all `chores_log` rows when a chore definition is
deleted, so the API intentionally exposes no chore `DELETE` route. Deactivation
sets `active=0` and preserves execution history.
