import csv
from pathlib import Path

from build_lookups import lookups


def validate():

    catalog = Path("/opt/Nuestra-Casita/catalog/products.csv")

    print("=" * 60)
    print("Catalog Validator")
    print("=" * 60)

    required_columns = [
        "Product",
        "Product Group",
        "Default Location",
        "Stock Unit",
        "Minimum Stock",
        "Notes",
    ]

    with catalog.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        missing = [c for c in required_columns if c not in reader.fieldnames]

        if missing:
            print("Missing columns:")
            for c in missing:
                print("-", c)
            return False

        seen = set()
        errors = 0

        for row_number, row in enumerate(reader, start=2):

            name = row["Product"].strip()

            if name.casefold() in seen:
                print(f"Duplicate product: {name} (row {row_number})")
                errors += 1

            seen.add(name.casefold())

            if row["Product Group"] not in lookups["groups"]:
                print(f"Unknown Product Group: {row['Product Group']}")
                errors += 1

            if row["Default Location"] not in lookups["locations"]:
                print(f"Unknown Location: {row['Default Location']}")
                errors += 1

            if row["Stock Unit"] not in lookups["units"]:
                print(f"Unknown Quantity Unit: {row['Stock Unit']}")
                errors += 1

    if errors == 0:
        print("✅ Catalog validation passed!")
        return True

    print(f"\nFound {errors} errors.")
    return False
