# Milestone 16 — iPad UI Handoff

The browser UI can rely on the version-1 endpoints and envelope in
`DASHBOARD_API.md`.

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
and offline writes remain unsupported. Build a same-origin responsive web app
behind the same private HTTPS reverse proxy so the HTTP-only cookie works
naturally on the kitchen iPad without broad CORS.
