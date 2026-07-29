# Nuestra Casita Architecture

## 1. Project Vision

Nuestra Casita is a household-management platform designed around a
touch-friendly visual dashboard installed in the kitchen.

The dashboard should combine information and actions from:

- Nextcloud Calendar
- Grocy
- Actual Budget
- Home Assistant
- Immich
- Weather services

Family members should interact primarily with the Nuestra Casita dashboard
rather than needing to understand or navigate each underlying application.

Nuestra Casita is not intended to replace these applications. It acts as the
integration, automation, and presentation layer that makes them feel like one
cohesive household system.

---

## 2. Primary User Experience

The kitchen dashboard is the primary interface.

It should answer common household questions quickly:

- What is happening today?
- What is for dinner?
- What groceries are needed?
- What food is running low?
- How much remains in the grocery budget?
- Are there chores or household alerts requiring attention?
- What is the current weather?
- Are there upcoming bills or important appointments?

The interface must be:

- Touch-friendly
- Easy to read from several feet away
- Family-friendly
- Fast to navigate
- Useful without exposing technical service names
- Functional on a wall-mounted or countertop display

---

## 3. Source-of-Truth Rules

Each category of household data must have one authoritative owner.

| Data category | Source of truth |
|---|---|
| Products and pantry inventory | Grocy |
| Shopping list | Grocy |
| Recipes | Grocy |
| Meal planning | Grocy initially |
| Family calendar | Nextcloud Calendar |
| Household budget | Actual Budget |
| Devices and sensors | Home Assistant |
| Chores and household states | Home Assistant initially |
| Photos and memories | Immich |
| Files and shared documents | Nextcloud |
| Dashboard presentation | Nuestra Casita |
| Cross-service workflows | Nuestra Casita |

Nuestra Casita may cache information for performance, but it must not silently
become a competing source of truth.

---

## 4. System Responsibilities

### 4.1 Nuestra Casita

Nuestra Casita is responsible for:

- Reading information from integrated services
- Normalizing data into a consistent internal format
- Coordinating workflows involving multiple services
- Providing a dashboard API
- Providing a command-line interface for administration
- Validating catalog and configuration files
- Synchronizing managed records
- Presenting household information in a family-friendly format
- Recording synchronization results and errors

### 4.2 Grocy

Grocy is responsible for:

- Product definitions
- Pantry inventory
- Shopping lists
- Recipes
- Meal planning
- Quantity units
- Product groups
- Storage locations
- Stores

### 4.3 Nextcloud

Nextcloud is responsible for:

- Family calendars
- Shared files
- Contacts when needed
- Tasks when adopted by the project

### 4.4 Actual Budget

Actual Budget is responsible for:

- Accounts
- Transactions
- Categories
- Monthly budgets
- Grocery spending
- Bills and recurring expenses

Nuestra Casita should initially read summarized budget information. It should
not create, edit, or delete financial transactions until that behavior has been
designed and explicitly enabled.

### 4.5 Home Assistant

Home Assistant is responsible for:

- Device state
- Sensors
- Lights
- Appliances
- Presence
- Household automations
- Chore-related entities when appropriate
- Alert delivery

Nuestra Casita may invoke Home Assistant services or expose information that
Home Assistant can consume.

### 4.6 Immich

Immich is responsible for:

- Household photos
- Albums
- Memories
- Photo rotation for the dashboard

---

## 5. High-Level Architecture

```text
                       Kitchen Dashboard
                              |
                              v
                    Nuestra Casita Web UI
                              |
                              v
                    Nuestra Casita API
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
       Domain Services   Sync Framework   Workflow Engine
             |                |                |
             +----------------+----------------+
                              |
               +--------------+--------------+
               |              |              |
               v              v              v
             Grocy        Nextcloud      Actual Budget
               |
               +--------------+--------------+
                              |
                         Home Assistant
                              |
                            Immich
