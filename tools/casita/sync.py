import csv
from pathlib import Path

from casita.apply import apply_plan
from casita.diff import compare_product
from casita.grocy import get
from casita.lookups import build_lookups
from casita.plan import build_plan


CATALOG = Path("/opt/Nuestra-Casita/catalog")


def load_catalog_products():
    """
    Load products from catalog/products.csv.
    """

    catalog_path = CATALOG / "products.csv"

    with open(
        catalog_path,
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def load_grocy_products():
    """
    Load all products from Grocy.
    """

    return get("/objects/products")


def print_execution_plan(plan):
    """
    Display the completed execution plan.
    """

    print("Execution Plan")
    print("=" * 40)
    print()

    for item in plan["update"]:
        print(f"~ UPDATE    {item['name']}")

        for change in item["changes"]:
            print(f"    {change['label']}")
            print(
                f"      Grocy:   "
                f"{change['grocy_display']}"
            )
            print(
                f"      Catalog: "
                f"{change['catalog_display']}"
            )

        print()

    for item in plan["create"]:
        print(f"+ CREATE    {item['name']}")

    if plan["create"]:
        print()

    print("=" * 40)
    print("Summary")
    print("=" * 40)

    print(f"Match : {len(plan['match'])}")
    print(f"Update: {len(plan['update'])}")
    print(f"Create: {len(plan['create'])}")


def sync_products(apply=False):
    """
    Compare catalog products with Grocy and build an execution plan.
    """

    print("Loading catalog...")

    catalog_products = load_catalog_products()

    print(f"Catalog products: {len(catalog_products)}")
    print()

    print("Loading Grocy...")

    grocy_product_list = load_grocy_products()

    print(f"Grocy products: {len(grocy_product_list)}")
    print()

    print("Loading lookup tables...")

    lookups = build_lookups()

    print("Lookup tables loaded.")
    print()

    grocy_products_by_name = {
        product["name"].strip().lower(): product
        for product in grocy_product_list
    }

    plan = build_plan()

    for catalog_product in catalog_products:

        name = catalog_product["Product"].strip()
        product_key = name.lower()

        grocy_product = grocy_products_by_name.get(product_key)

        if grocy_product is None:

            plan["create"].append(
                {
                    "name": name,
                    "catalog": catalog_product,
                }
            )

            continue

        differences = compare_product(
            catalog_product,
            grocy_product,
            lookups,
        )

        if differences:

            plan["update"].append(
                {
                    "name": name,
                    "product_id": grocy_product["id"],
                    "catalog": catalog_product,
                    "grocy": grocy_product,
                    "changes": differences,
                }
            )

        else:

            plan["match"].append(
                {
                    "name": name,
                    "product_id": grocy_product["id"],
                    "catalog": catalog_product,
                    "grocy": grocy_product,
                }
            )

    print_execution_plan(plan)

    if apply:

        apply_plan(plan)

    else:

        print()
        print("=" * 40)
        print("Dry Run")
        print("=" * 40)
        print()
        print("No changes were made.")
        print()
        print("Run again with:")
        print()
        print("    python tools/casita.py sync products --apply")

    return plan
