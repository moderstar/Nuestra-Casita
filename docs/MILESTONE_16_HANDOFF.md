# Milestone 16 — Kitchen Dashboard Implementation

The browser UI described by this handoff is implemented in `frontend/`. See
`KITCHEN_DASHBOARD.md` for architecture, development, deployment, testing, and
troubleshooting guidance.

- Login through `POST /api/v1/session` using same-origin credentialed requests.
- Never persist the household password or a backend token in JavaScript.
- Render Inventory, Shopping Lists, Recipes, Chores, Meal Plan, and Tasks.
- Treat Decimal strings as decimal text and dates as household-local display.
- Distinguish `available`, `empty`, and `degraded`; show section retry states.
- Refresh Shopping every 30 seconds; Chores, Meal Plan, and Tasks every minute;
  Inventory and Recipes every five minutes; refresh on foreground resume.
- On `401`, show login. On network failure, retain the last snapshot marked
  stale. The server has no cache.

Calendar, budget, Home Assistant controls, photos, notifications, mutations,
and offline writes remain unsupported. The implemented Nginx service provides
the same-origin `/api/` reverse proxy needed by the HTTP-only session cookie.
