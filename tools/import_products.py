import csv
from pathlib import Path

import requests

from casita.grocy import get, post


CATALOG_FILE = Path("/opt/Nuestra-Casita/catalog/products.csv")


def name_to_id(entity: str) -> dict[str, int]:
    return {
        item["name"].strip().casefold(): item["id"]
        for item in get(f"/objects/{entity}")
        if item.get("active", 1)
    }


def require_id(
    lookup: dict[str, int],
    value: str,
    field_name: str,
    row_number: int,
) -> int:
    key = value.strip().casefold()

    if key not in lookup:
        raise ValueError(
            f'Row {row_number}: {field_name} "{value}" does not exist in Grocy'
        )

    return lookup[key]


print("=" * 60)
print("Nuestra Casita Product Importer")
print("=" * 60)

locations = name_to_id("locations")
units = name_to_id("quantity_units")
groups = name_to_id("product_groups")
existing_products = name_to_id("products")

created = 0
skipped = 0
errors = 0

with CATALOG_FILE.open(newline="", encoding="utf-8-sig") as csv_file:
    reader = csv.DictReader(csv_file)

    required_columns = {
        "Product",
        "Product Group",
        "Default Location",
        "Stock Unit",
        "Minimum Stock",
        "Notes",
    }

    missing_columns = required_columns - set(reader.fieldnames or [])

    if missing_columns:
        raise RuntimeError(
            "Missing CSV columns: " + ", ".join(sorted(missing_columns))
        )

    for row_number, row in enumerate(reader, start=2):
        product_name = row["Product"].strip()

        if not product_name:
            print(f"ERROR row {row_number}: Product name is empty")
            errors += 1
            continue

        if product_name.casefold() in existing_products:
            print(f"SKIP: {product_name} already exists")
            skipped += 1
            continue

        try:
            location_id = require_id(
                locations,
                row["Default Location"],
                "Location",
                row_number,
            )
            unit_id = require_id(
                units,
                row["Stock Unit"],
                "Quantity unit",
                row_number,
            )
            group_id = require_id(
                groups,
                row["Product Group"],
                "Product group",
                row_number,
            )

            minimum_stock = int(row["Minimum Stock"] or 0)

            payload = {
                "name": product_name,
                "description": row["Notes"].strip() or None,
                "product_group_id": group_id,
                "location_id": location_id,
                "qu_id_purchase": unit_id,
                "qu_id_stock": unit_id,
                "qu_id_consume": unit_id,
                "qu_id_price": unit_id,
                "min_stock_amount": minimum_stock,
                "default_purchase_price_type": 1,
                "active": 1,
            }

            result = post("/objects/products", payload)

            created_id = None
            if isinstance(result, dict):
                created_id = result.get("created_object_id")

            existing_products[product_name.casefold()] = created_id or -1
            created += 1
            print(f"CREATED: {product_name}")

        except (ValueError, TypeError, requests.RequestException) as error:
            errors += 1
            print(f"ERROR row {row_number} ({product_name}): {error}")

            if isinstance(error, requests.HTTPError):
                print(f"Grocy response: {error.response.text}")

print("\n" + "=" * 60)
print(f"Created: {created}")
print(f"Skipped: {skipped}")
print(f"Errors:  {errors}")
print("=" * 60)
