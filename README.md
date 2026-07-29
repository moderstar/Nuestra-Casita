# Nuestra Casita

Nuestra Casita is the orchestration platform for a self-hosted household.

It provides one household language above specialized systems such as Grocy,
Home Assistant, Nextcloud, Actual Budget, and Immich. Those applications keep
their native strengths; Nuestra Casita translates, synchronizes, and combines
their data without exposing vendor APIs to future clients.

## Current Capabilities

- Git-backed declarative synchronization for Grocy 4.6
- Generic planning, comparison, identity, apply, and ordered orchestration
- Backend-neutral household domain models
- Common integration and synchronization contracts
- Versioned internal contract for the future kitchen dashboard
- Architecture designed for reproducible Docker and Proxmox deployments

No dashboard, frontend, API server, authentication system, or platform
database is implemented yet.

## Architecture

- [Core architecture](docs/CORE_ARCHITECTURE.md)
- [Application layer](docs/APPLICATION_LAYER.md)
- [Composition root](docs/COMPOSITION_ROOT.md)
- [Grocy read adapter](docs/GROCY_READ_ADAPTER.md)
- [Integration contract](docs/INTEGRATION_CONTRACT.md)
- [Dashboard contract](docs/DASHBOARD_CONTRACT.md)
- [Grocy integration architecture](docs/ARCHITECTURE.md)
- [Project roadmap](PROJECT_ROADMAP.md)
- [Grocy 4.6 API inventory](docs/GROCY_4_6_API_RESOURCES.md)

## Project Structure

```text
catalog/                  Git-backed declarative catalogs
docs/                     Platform and integration documentation
tools/casita/domain/      Household domain models
tools/casita/integrations Integration contracts
tools/casita/integrations/grocy
                          Grocy client and domain translation
tools/casita/application/ Household services and dashboard assembly
tools/casita/bootstrap/   Application construction and object lifetime
tools/casita/dashboard/   Internal dashboard contract
tools/casita/payloads/    Grocy payload builders
tools/casita/resources/   Grocy resource definitions
```

## Grocy Synchronization

Dry-run every registered Grocy resource:

```bash
python tools/casita.py sync all
```

Apply the generated plans:

```bash
python tools/casita.py sync all --apply
```

Individual resource commands remain available. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the complete list and
dependency order.

## Long-Term Direction

The primary household interface will be a wall-mounted kitchen touchscreen
that consumes only Nuestra Casita models. It will combine inventory, shopping,
recipes, chores, calendars, finances, home state, notifications, and family
media without requiring household members to navigate separate applications.
