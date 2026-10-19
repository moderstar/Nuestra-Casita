# Catalog Conventions

Nuestra Casita catalogs contain only household definitions intentionally
managed from Git. Native Grocy rows absent from a catalog remain unmanaged and
are never deleted by synchronization.

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
