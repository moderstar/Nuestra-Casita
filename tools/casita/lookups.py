from pprint import pprint

from casita.grocy import get


def build_lookups():
    lookups = {
        "locations": {},
        "locations_by_id": {},

        "units": {},
        "units_by_id": {},

        "groups": {},
        "groups_by_id": {},

        "stores": {},
        "stores_by_id": {},

        "products": {},
        "products_by_id": {},

        "recipes": {},
        "recipes_by_id": {},
    }

    for row in get("/objects/locations"):
        lookups["locations"][row["name"]] = row["id"]
        lookups["locations_by_id"][row["id"]] = row["name"]

    for row in get("/objects/quantity_units"):
        lookups["units"][row["name"]] = row["id"]
        lookups["units_by_id"][row["id"]] = row["name"]

    for row in get("/objects/product_groups"):
        lookups["groups"][row["name"]] = row["id"]
        lookups["groups_by_id"][row["id"]] = row["name"]

    for row in get("/objects/shopping_locations"):
        lookups["stores"][row["name"]] = row["id"]
        lookups["stores_by_id"][row["id"]] = row["name"]

    for row in get("/objects/products"):
        lookups["products"][row["name"]] = row["id"]
        lookups["products_by_id"][row["id"]] = row["name"]

    for row in get("/objects/recipes?query[]=type=normal"):
        lookups["recipes"][row["name"]] = row["id"]
        lookups["recipes_by_id"][row["id"]] = row["name"]

    return lookups


def show():
    pprint(build_lookups())
