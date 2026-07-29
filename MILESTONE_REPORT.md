# Milestone 3 Report: Quantity Units

## Summary

Milestone 3 adds Quantity Units as a first-class Nuestra Casita resource.

Quantity Units now use the existing registry, generic planning engine, generic
apply engine, payload-builder interface, resource-definition interface, and
generic CLI used by Products and Product Groups.

The managed Grocy 4.6 fields are:

- `name`
- `name_plural`
- `plural_forms`
- `description`
- `active`

## Modified Files

### Added

- `catalog/quantity_units.csv`
- `tools/casita/payloads/quantity_units.py`
- `tools/casita/resources/quantity_units.py`
- `MILESTONE_REPORT.md`

### Updated

- `tools/casita/payloads/__init__.py`
- `tools/casita/resources/__init__.py`
- `tools/casita/registry.py`
- `docs/ARCHITECTURE.md`
- `PROJECT_ROADMAP.md`

## Verification Performed

- Confirmed the Quantity Units schema against the Grocy 4.6.0 source.
- Compiled all Python files under `tools`.
- Confirmed `quantity-units` is present in the resource registry.
- Verified Quantity Unit planning with four create operations.
- Verified Quantity Unit payload generation for all managed Grocy 4.6 fields.
- Verified Quantity Unit apply routing to `/objects/quantity_units`.
- Verified Quantity Units do not load lookup tables.
- Verified all required Quantity Units, Product Groups, and Products CLI
  commands against an isolated Grocy 4.6-compatible API fixture.
- Ran `git diff --check`.

## Commands Executed

```bash
python -m compileall -q tools
python tools/casita.py sync quantity-units
python tools/casita.py sync quantity-units --apply
python tools/casita.py sync product-groups
python tools/casita.py sync product-groups --apply
python tools/casita.py sync products
python tools/casita.py sync products --apply
git diff --check
```

Every required synchronization command completed with exit code 0.

## Architectural Changes

No framework redesign or unrelated refactoring was performed.

The only architectural extension was registering one additional resource,
`quantity-units`, through the existing resource registry. The generic CLI
discovers the new command from that registry without Quantity Unit-specific
command routing.

## Known Limitations

- The six-command verification used an isolated Grocy 4.6-compatible API
  fixture and did not modify the live Grocy instance.
- The initial catalog manages the four Quantity Units currently referenced by
  `catalog/products.csv`: Each, Bag, Package, and Bottle.
- Quantity Units already present in Grocy but absent from
  `catalog/quantity_units.csv` are left unmanaged; the synchronization engine
  does not delete them.
- Quantity Unit conversions are a separate Grocy resource and are not part of
  this milestone.

## Suggested Next Milestone

Milestone 4 should implement Locations as the next first-class Grocy resource,
using the same focused resource, payload, registry, planning, apply, CLI, and
verification pattern.
