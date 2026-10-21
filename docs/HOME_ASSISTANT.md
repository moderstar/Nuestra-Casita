# Home Assistant Read-Only Integration

## Ownership and architecture

Home Assistant remains authoritative for entity definitions, current states,
attributes, and availability. Nuestra Casita performs authenticated REST reads
and maps selected entities to the backend-neutral `Device` model:

```text
Kitchen dashboard -> Dashboard API -> DeviceService -> Home Assistant adapter
```

Home Assistant REST payloads and credentials stay inside
`casita.integrations.home_assistant`. The browser receives only normalized
device records. This milestone adds no service-call client, control contract,
automation execution, database, cache, or synchronization resource.

## Create a long-lived access token

1. Sign in to Home Assistant with the account Nuestra Casita should use.
2. Open the user profile from the lower-left account menu.
3. Find **Long-lived access tokens** and select **Create Token**.
4. Give it a recognizable name such as `Nuestra Casita Dashboard`.
5. Copy the token when Home Assistant shows it; it is displayed only once.
6. Store it only in `/opt/Nuestra-Casita/.env` on the Docker VM.

Home Assistant's official REST documentation describes Bearer-token
authentication and the `/api/states` response used here:
<https://developers.home-assistant.io/docs/api/rest>.

Do not paste the token into Git, frontend files, screenshots, issue reports, or
shell history. Home Assistant long-lived tokens inherit the permissions of the
user that created them; use a dedicated account with the least privileges your
Home Assistant deployment supports.

## Configuration

```dotenv
HOME_ASSISTANT_URL=http://192.168.8.157:8123
HOME_ASSISTANT_TOKEN=replace-with-home-assistant-long-lived-access-token
HOME_ASSISTANT_ENTITY_IDS=sensor.kitchen_temperature,binary_sensor.garage_door
CASITA_REQUEST_TIMEOUT_SECONDS=10
```

The URL and token must either both be present or both be absent. An absent
pair disables the integration safely. `HOME_ASSISTANT_ENTITY_IDS` is an exact,
comma-separated allowlist; an empty list exposes no entities. Duplicate IDs
are deduplicated while preserving order. IDs use Home Assistant's lowercase
`domain.object_id` form.

The same bounded 0.1–60 second timeout applies to Grocy and Home Assistant.
Configuration stays outside Git through the existing ignored `.env` file.

## State mapping

| Home Assistant value | Nuestra Casita availability | Display value |
| --- | --- | --- |
| `unavailable` | `unavailable` | Unavailable |
| `unknown` | `unknown` | Unknown |
| Any other state | `available` | State plus unit, when present |
| Allowlisted ID missing from `/api/states` | `unavailable` | Unavailable |

The entity domain becomes the Device kind. `friendly_name` becomes its name,
and `unit_of_measurement` becomes its unit. A bounded safe set of scalar
display attributes is retained: device class, battery level, brightness,
percentage, current/target temperature, humidity, HVAC action, and mode.
Location attributes and arbitrary nested payloads are not projected.

## Failure behavior

Authentication rejection, timeout, connection failure, non-success status,
invalid JSON, and malformed state rows fail only the Devices capability. The
dashboard marks Home Status stale/degraded while Grocy-backed sections remain
available. API responses never include the configured URL, token,
Authorization header, or raw Home Assistant response.

Troubleshooting from the Docker VM:

```bash
docker compose logs dashboard-api
docker exec nuestra-casita-dashboard-api-1 python -c \
  'import urllib.request; urllib.request.urlopen("http://192.168.8.157:8123/api/", timeout=5)'
```

An unauthenticated HTTP 401 confirms network reachability. Validate the token
through the deployed dashboard rather than placing it directly in a command.
