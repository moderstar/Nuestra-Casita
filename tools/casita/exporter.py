import csv
from pathlib import Path

from casita.grocy import get
from casita.lookups import build_lookups


CATALOG = Path("/opt/Nuestra-Casita/catalog")


def export_products():

    print("Loading lookup tables...")

    lookups = build_lookups()

    group_lookup = {v: k for k, v in lookups["groups"].items()}
    location_lookup = {v: k for k, v in lookups["locations"].items()}
    unit_lookup = {v: k for k, v in lookups["units"].items()}

    print("Downloading products from Grocy...")

    products = get("/objects/products")

    print(f"Found {len(products)} products.")

    print("Writing CSV...")

    with open(CATALOG / "products_export.csv", "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Product",
            "Product Group",
            "Default Location",
            "Stock Unit",
            "Minimum Stock",
        ])

        for product in products:

            writer.writerow([
                product["name"],
                group_lookup.get(product["product_group_id"], ""),
                location_lookup.get(product["location_id"], ""),
                unit_lookup.get(product["qu_id_stock"], ""),
                product["min_stock_amount"],
            ])

    print("Done.")
