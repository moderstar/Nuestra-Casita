# Catalog Conventions

Nuestra Casita catalogs contain only household definitions intentionally
managed from Git. Native Grocy rows absent from a catalog remain unmanaged and
are never deleted by synchronization.

## Equipment

`catalog/equipment.csv` contains:

| Column | Required | Meaning |
| --- | --- | --- |
| `Equipment` | Yes | Unique name and conservative synchronization identity |
| `Description` | No | Git-managed descriptive text |

The file starts header-only. Equipment names match case-insensitively after
trimming. Duplicate catalog names and ambiguous duplicate Grocy names stop
planning. Apply can create a named item or update its description only.
Instruction-manual files, Userfield values, creation timestamps, maintenance
information kept outside this entity, unmanaged rows, and deletions remain
Grocy-owned.

```bash
python tools/casita.py sync equipment
python tools/casita.py sync equipment --apply
```

## User Entity Definitions

`catalog/user_entities.csv` contains:

| Column | Required | Meaning |
| --- | --- | --- |
| `Name` | Yes | Immutable internal identifier: letters, numbers, underscores |
| `Caption` | Yes | User-facing name |
| `Description` | No | Definition description |
| `Show in Sidebar` | No | Boolean; blank defaults to enabled |
| `Icon CSS Class` | No | Optional Grocy sidebar icon class |

This CSV models only rows in Grocy's `userentities` definition table. Custom
fields remain in `catalog/userfields.csv` under entity
`userentity-<Name>`. User Entity records (`userobjects`) and all field values
are live Grocy data and are never cataloged, updated, migrated, or deleted.

The internal name is the identity and is never updated. Apply can create a
definition or update caption, description, sidebar visibility, and icon only.
A field-type change for a `userentity-*` Userfield is rejected as an
unsupported destructive migration. Renames and record migration require an
explicit future migration mechanism.

```bash
python tools/casita.py sync user-entities
python tools/casita.py sync user-entities --apply
```

## Quantity Unit Conversions

`catalog/quantity_unit_conversions.csv` has these columns:

| Column | Required | Meaning |
| --- | --- | --- |
| `From Quantity Unit` | Yes | Source Quantity Unit name |
| `To Quantity Unit` | Yes | Target Quantity Unit name |
| `Factor` | Yes | Positive decimal target amount for one source unit |
| `Product` | No | Blank for global/default scope; Product name for Product-specific scope |

Direction is explicit:

```text
1 From Quantity Unit = Factor To Quantity Units
```

For example, a factor of `6` from `Package` to `Each` means one Package is six
Each. The repository does not ship that example as household data; the
catalog starts empty so conversions are added only after the household has
chosen them.

Factors are parsed with decimal arithmetic. Zero, negative, nonnumeric,
infinite, and NaN factors are rejected. Source and target names must resolve
to existing Quantity Units and must differ. A Product-specific row must also
resolve to an existing Product.

The unique managed identity is Product scope plus the directional source and
target units. Duplicate rows and rows with the same identity but conflicting
factors are rejected before application. Reverse conversions are separate
directions; Grocy-derived reverse and transitive cache entries should not be
copied into this catalog.

Dry-run:

```bash
python tools/casita.py sync quantity-unit-conversions
```

Explicit apply:

```bash
python tools/casita.py sync quantity-unit-conversions --apply
```

Apply can create explicitly cataloged conversions or update the factor of an
identity already managed by the catalog. It does not delete conversions, so
unmanaged Grocy definitions are preserved.

## Product Barcodes

`catalog/product_barcodes.csv` has these columns:

| Column | Required | Meaning |
| --- | --- | --- |
| `Barcode` | Yes | Exact opaque barcode value; retained as text |
| `Product` | Yes | Product name resolved through the existing Product lookup |

The file intentionally starts with only its header. Barcode values are never
parsed as numbers, so leading zeros are preserved. Grocy 4.6 does not impose
a documented symbology or checksum restriction through this API; the catalog
therefore accepts non-empty strings rather than guessing a format policy.

Identity is the barcode value, matched case-insensitively to follow Grocy 4.6
lookup behavior. Duplicate values, including case-only variants, are rejected.
Multiple distinct barcodes may reference one Product. If a catalog barcode
already exists for a different Product, planning fails instead of producing a
reassignment.

Dry-run:

```bash
python tools/casita.py sync product-barcodes
```

Explicit apply:

```bash
python tools/casita.py sync product-barcodes --apply
```

Git is authoritative only for rows explicitly present in the catalog. Apply
creates missing associations; matching rows are no-ops. Unmanaged Grocy rows
are preserved, and synchronization never updates or deletes barcode rows.

## Tasks

`catalog/tasks.csv` has these columns:

| Column | Required | Meaning |
| --- | --- | --- |
| `Task` | Yes | Stable Task name used for exact normalized matching |
| `Description` | No | Git-managed definition text |
| `Due Date` | No | Date-only `YYYY-MM-DD` value; blank means no due date |
| `Task Category` | No | Existing Task Category name; blank means uncategorized |

The catalog intentionally starts with only its header. Task Categories must
exist before referenced Tasks are applied, and `sync all` enforces that order.
Invalid dates and missing categories fail during planning.

Task names are matched case-insensitively after trimming. Grocy 4.6 has no
external Task key or unique-name constraint, so duplicate names on either side
are rejected as ambiguous. A catalog row with an exact identity is explicitly
managed; Grocy Tasks absent from Git are preserved.

Dry-run and apply:

```bash
python tools/casita.py sync tasks
python tools/casita.py sync tasks --apply
```

Only `description`, `due_date`, and `category_id` can be updated. Completion,
completion timestamps, assignment, creation timestamps, userfields, and other
runtime state are never placed in synchronization payloads. No Task is deleted
for being absent from the catalog.

## Meal Plan Sections

`catalog/meal_plan_sections.csv` contains:

| Column | Required | Meaning |
| --- | --- | --- |
| `Meal Plan Section` | Yes | Unique section name and synchronization identity |
| `Sort Number` | No | Nonnegative presentation order |
| `Time` | No | Presentation time in 24-hour `HH:MM` format |

The catalog starts header-only. Explicit rows can be created, matched, or have
their sort number/time updated. Renaming is represented as a new section so an
unrelated or user-created section is never silently renamed. Grocy's internal
blank section is filtered from synchronization.

## Meal Plan Entries

`catalog/meal_plan.csv` contains:

| Column | Required | Meaning |
| --- | --- | --- |
| `Day` | Yes | Entry date in `YYYY-MM-DD` format |
| `Meal Plan Section` | Yes | Existing managed or Grocy section name |
| `Entry Type` | Yes | `recipe`, `product`, or `note` |
| `Recipe` | Recipe only | Existing Recipe name |
| `Servings` | No | Positive decimal; defaults to `1` for Recipe entries |
| `Product` | Product only | Existing Product name |
| `Amount` | Product only | Positive decimal amount |
| `Quantity Unit` | Product only | Existing Quantity Unit name |
| `Note` | Note only | Required free text and part of identity |

Type-irrelevant values are rejected rather than silently discarded. Identity
is the day, resolved section, type, and type-specific Recipe, Product, or exact
note content. Exact duplicate identities are unsupported because Grocy has no
external ownership key; ambiguity blocks planning.

Dry-run and apply:

```bash
python tools/casita.py sync meal-plan-sections
python tools/casita.py sync meal-plan-sections --apply
python tools/casita.py sync meal-plan
python tools/casita.py sync meal-plan --apply
```

Recipe servings and Product amount/unit may be updated after an unambiguous
identity match. Day, section, type, referenced Recipe/Product, note content,
completion state, and creation timestamps are never updated. Missing catalog
rows never cause deletions, so user-created Grocy plans remain intact.
