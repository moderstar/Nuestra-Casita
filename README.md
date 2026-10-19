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

The terminal dashboard and unified application CLI are implemented. No web
frontend, API server, authentication system, or platform database is
implemented yet.

## Architecture

- [Core architecture](docs/CORE_ARCHITECTURE.md)
- [Application layer](docs/APPLICATION_LAYER.md)
- [Composition root](docs/COMPOSITION_ROOT.md)
- [Grocy read adapter](docs/GROCY_READ_ADAPTER.md)
- [Dashboard and command framework](docs/COMMAND_FRAMEWORK.md)
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

Show platform and Grocy status:

```bash
python tools/casita.py dashboard
```

Run actionable diagnostics:

```bash
python tools/casita.py doctor
```

Inspect Grocy-owned shopping lists and their current items without changing
household activity:

```bash
python tools/casita.py shopping-lists
```

Dry-run every registered Grocy resource:

```bash
python tools/casita.py sync all
```

The shorter form defaults to the same dependency-aware orchestration:

```bash
python tools/casita.py sync
```

Apply the generated plans:

```bash
python tools/casita.py sync all --apply
```

Individual resource commands remain available. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the complete list and
dependency order.

Shopping lists are intentionally not part of declarative synchronization.
Products and other master data can remain Git-managed, while checked state,
quantities, notes, and list membership remain live Grocy-owned activity.

Inspect managed Quantity Unit Conversions without changing Grocy:

```bash
python tools/casita.py sync quantity-unit-conversions
```

Apply only the explicitly cataloged conversion creates or factor updates:

```bash
python tools/casita.py sync quantity-unit-conversions --apply
```

Validate and preview Git-managed Product Barcode associations:

```bash
python tools/casita.py sync product-barcodes
```

Create only missing, explicitly cataloged associations:

```bash
python tools/casita.py sync product-barcodes --apply
```

Existing Grocy barcodes absent from the catalog are preserved, and an existing
barcode is never silently reassigned to a different Product.

Preview or apply Git-managed non-recurring Task definitions:

```bash
python tools/casita.py sync tasks
python tools/casita.py sync tasks --apply
```

Task completion, completion timestamps, user assignments, and Grocy-only Tasks
remain owned by Grocy and are never overwritten by catalog synchronization.

Preview or apply Meal Plan Sections and explicitly managed Meal Plan Entries:

```bash
python tools/casita.py sync meal-plan-sections
python tools/casita.py sync meal-plan-sections --apply
python tools/casita.py sync meal-plan
python tools/casita.py sync meal-plan --apply
```

Unmanaged Grocy plans and completion state are preserved. Entry moves,
retargeting, ambiguous duplicates, and automatic deletion are not performed.

## Long-Term Direction

The primary household interface will be a wall-mounted kitchen touchscreen
that consumes only Nuestra Casita models. It will combine inventory, shopping,
recipes, chores, calendars, finances, home state, notifications, and family
media without requiring household members to navigate separate applications.
