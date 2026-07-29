# Nuestra Casita Project Roadmap

## Vision

Nuestra Casita is the central orchestration platform for the household and
homelab.

It provides one authoritative source for inventory, finances, calendars,
automation, and media while synchronizing data across self-hosted applications
through a modular integration framework.

Nuestra Casita is not intended to replace Grocy, Nextcloud, Actual Budget,
Home Assistant, Immich, Paperless, or other specialized applications. It is
the integration layer that allows those systems to communicate and remain
reproducible.

## Long-Term Goal

The primary household interface will be a wall-mounted touchscreen tablet in
the kitchen.

The tablet should provide one unified experience for:

- Inventory and expiration tracking
- Meal planning and recipes
- Shopping lists
- Chores and household tasks
- Family calendars and contacts
- Household documents
- Personal budgeting and household expenses
- Home automation
- Family photos and media

## Design Principles

Nuestra Casita should remain:

- Self-hosted
- Open source where possible
- Version controlled
- Fully reproducible from Git
- Docker and Proxmox friendly
- Modular and expandable
- Safe to run in dry-run mode before applying changes

Every piece of household information should have one authoritative source.

Examples include:

- Products in version-controlled CSV catalogs
- Recipes in Git
- Household configuration in Git
- Infrastructure configuration in Git
- Integration-specific data managed through explicit synchronization rules

## Integration Architecture

Nuestra Casita now has backend-neutral domain, integration, synchronization,
and dashboard contracts. External systems translate their APIs into household
models before data reaches application services or clients.

Planned integration targets include:

- Grocy
- Nextcloud
- Actual Budget
- Home Assistant
- Immich
- Paperless
- MQTT
- Future self-hosted services

The registry, resource definitions, payload builders, planning engine,
synchronization engine, and apply engine form the reusable foundation for
these integrations.

## Platform Foundation

- [x] Define backend-neutral household domain models
- [x] Define common integration capabilities and read contract
- [x] Define optional declarative synchronization contract
- [x] Define the versioned kitchen-dashboard data contract
- [x] Document capability ownership and cache expectations
- [x] Add instance-scoped integration discovery and capability ownership
- [x] Add household capability services
- [x] Add backend-neutral dashboard snapshot assembly
- [x] Add explicit composition root and application object lifetime
- [x] Add environment-backed household and integration configuration
- [x] Add Grocy read adapter for Inventory, Shopping, Recipes, and Chores
- [x] Add unified dashboard and command framework
- [x] Route synchronization and diagnostics through application services
- [x] Add application service unit tests and command regression verification
- [ ] Add remaining Grocy platform read capabilities when domain needs emerge
- [ ] Select persistence and caching only when required by an integration
- [ ] Add normalized platform events and notifications

## Current Development Priority

The current priority is preserving the robust Grocy 4.6 integration while
building the orchestration layer one demonstrated integration at a time.

Products, Product Groups, Quantity Units, Locations, Shopping Locations,
Task Categories, Chores, Batteries, Recipe Definitions, Recipe Positions,
and Userfields are implemented through the generic synchronization framework.

### Grocy Roadmap

- [x] Products
- [x] Product Groups framework integration
- [x] Verify Product Groups against the live Grocy 4.6 instance
- [x] Quantity Units
- [x] Locations
- [x] Shopping Locations
- [x] Task Categories
- [x] Chores
- [x] Batteries
- [x] Recipe Definitions
- [x] Recipe Positions
- [x] Userfields
- [ ] Shopping Lists
- [ ] Quantity Unit Conversions
- [ ] Product Barcodes
- [ ] Tasks
- [ ] Meal Plan Sections and Meal Plan
- [ ] Equipment
- [ ] User Entities
- [ ] Refine the generic comparison engine where appropriate
- [ ] Add automated tests
- [x] Add a `sync all` command

## Next Integration Phases

The next integration should exercise the new platform contracts before
additional infrastructure is introduced.

### Home Assistant

- Expose household data to dashboards and automations
- Connect inventory and chore states to household workflows
- Support the future kitchen tablet interface

### Nextcloud

- Synchronize family calendar information
- Integrate tasks and contacts
- Connect household documents where appropriate

### Actual Budget

- Synchronize household budgeting information
- Support expense tracking, cash flow, and financial planning
- Connect shopping and household spending workflows where appropriate

### Immich

- Integrate family photo and media workflows
- Provide selected media experiences through the household dashboard

### Paperless

- Connect searchable household documents
- Link records and documents to relevant household workflows

### MQTT

- Publish and consume lightweight household events
- Connect Nuestra Casita to sensors, automations, and future services

## Kitchen Dashboard

The kitchen dashboard is the eventual unified user interface for Nuestra
Casita.

It should bring together the connected systems without forcing household
members to navigate between unrelated applications. The dashboard should be
touch-friendly, reliable, and useful for everyday household activity.

Initial dashboard areas are expected to include:

- Today and upcoming family calendar events
- Shopping list
- Expiring inventory
- Meal plan
- Chores and tasks
- Household budget summary
- Home status and common automations
- Family photos

The versioned internal dashboard contract is now defined. Dashboard UI,
transport, authentication, and deployment remain intentionally deferred.

## Reproducibility Goal

The complete system should be recoverable after reinstalling Proxmox.

Git should contain the catalogs, configuration, integration definitions,
documentation, and infrastructure instructions required to rebuild Nuestra
Casita and reconnect it to the self-hosted applications it orchestrates.

## Project Direction

Development will continue one integration and one capability at a time while
preserving the generic architecture.

Short-term work should solve the immediate Grocy synchronization milestones
without narrowing Nuestra Casita into a Grocy-only tool. Every completed
resource should strengthen the reusable orchestration foundation for the
larger household platform.
