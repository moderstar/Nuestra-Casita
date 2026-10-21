# Kitchen Dashboard Frontend

Milestone 19 extends the React and TypeScript interface for the version-1
Dashboard API. It is designed for an iPad in landscape orientation and adapts
to portrait tablets, desktop browsers, and phones.

## Architecture

The browser contains presentation logic only. It never calls Grocy, stores a
credential, or reproduces household business rules.

```text
Browser -> kitchen-dashboard (Nginx) -> /api proxy -> dashboard-api -> services
```

`frontend/src/types.ts` mirrors the backend-neutral version-1 response.
`frontend/src/api.ts` is the only HTTP client. Page and widget components render
the normalized snapshot and support available, empty, degraded, and stale
states. All presented data comes from the API.

Supported pages are Home, Home Status, Shopping, Inventory, Recipes, Meal
Plan, Chores, and Tasks. Home Status displays only configured Home Assistant
entities with their friendly name, domain, state, unit, and availability. It
is intentionally read-only and contains no toggles, sliders, service calls, or
automation actions. Shopping supports product search, free-text items, decimal quantities,
multiple lists, purchased state, and confirmed removal. Chores can be created,
edited, activated, deactivated, assigned, and completed through Grocy-native
operations. Daily, weekly, monthly, manual, hourly, yearly, and adaptive
schedules are supported. Successful writes trigger an authoritative dashboard
refresh before confirmation is shown.

Grocy owns chore definitions, schedules, assignment rotation, and execution
history. Start dates are disabled after the first execution, matching Grocy's
own restriction. Deactivate replaces Delete because Grocy 4.6 cascades chore
deletion to its execution journal.

## Authentication

The login form sends `{"password":"..."}` to `POST /api/v1/session` with
`credentials: "include"`. The API sets its signed, expiring, HTTP-only cookie.
JavaScript receives neither the session cookie nor backend secrets. A `401`
from any dashboard request returns the user to login. Logout calls
`DELETE /api/v1/session` and clears local view state. A signed double-submit
CSRF token protects logout and activity mutations, and an idempotency key
protects each submitted write from duplicate taps or retries.

Do not store `CASITA_API_PASSWORD`, `CASITA_API_SESSION_SECRET`,
`GROCY_API_KEY`, or `HOME_ASSISTANT_TOKEN` in frontend files or browser
storage.

## Local development

Run the Dashboard API on `127.0.0.1:8080`, then:

```bash
cd frontend
npm ci
npm run dev
```

Vite serves the UI at `http://localhost:5173` and proxies `/api` to the local
API. For plain HTTP development set `CASITA_API_COOKIE_SECURE=0`; otherwise the
browser correctly refuses to send the HTTPS-only cookie.

Validation commands:

```bash
cd frontend
npm run typecheck
npm test
npm run build
```

## Refresh and failure behavior

The complete dashboard is fetched after authentication, every 60 seconds while
the document is visible, on foreground resume, and when Refresh is selected.
Polling pauses while the page is hidden. A temporary network failure preserves
the previous snapshot and marks it stale. Backend degraded state and stale
sections remain visible without exposing upstream error details.

The current API returns a complete aggregate, so one aggregate refresh is used
instead of separate overlapping section polls. Future contract versions can
adopt section-specific refresh without changing page components.

## Accessibility and responsive behavior

- Primary controls meet or exceed a 44 CSS-pixel touch target.
- Navigation exposes `aria-current`; authentication and degraded states use
  appropriate labels and status regions.
- Layouts use Grid and Flexbox without document-level horizontal scrolling.
- iOS safe-area insets are respected.
- Light, dark, and system themes are supported.
- Reduced-motion preferences are respected.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Login repeats immediately | For HTTP testing, set `CASITA_API_COOKIE_SECURE=0`; use `1` behind HTTPS. |
| `502 Bad Gateway` | Confirm `dashboard-api` is healthy on the Compose network. |
| UI only works on the Docker VM | Bind `CASITA_FRONTEND_BIND_ADDRESS` to the VM LAN IP or `0.0.0.0`. |
| Old UI after an update | Reload once; `index.html` is not cached and hashed assets are immutable. |
| Limited/stale banner | Check `docker compose logs dashboard-api`; prior data is intentionally retained. |
| Home Status is empty | Configure `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`, and the comma-separated `HOME_ASSISTANT_ENTITY_IDS` allowlist. |
| Home Status is limited | Verify the URL from the API container, token validity, and exact entity IDs in Home Assistant Developer Tools. |

Calendar, budgets, Home Assistant controls, media, notifications, offline
writes, and public internet exposure remain future work.
