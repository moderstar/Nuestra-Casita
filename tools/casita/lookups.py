from pprint import pprint

from casita.grocy import get


def build_lookups():
    lookups = {
        "locations": {},
        "units": {},
        "groups": {},
        "stores": {},
    }

    for row in get("/objects/locations"):
        lookups["locations"][row["name"]] = row["id"]

    for row in get("/objects/quantity_units"):
        lookups["units"][row["name"]] = row["id"]

    for row in get("/objects/product_groups"):
        lookups["groups"][row["name"]] = row["id"]

    for row in get("/objects/shopping_locations"):
        lookups["stores"][row["name"]] = row["id"]

    return lookups


def show():
    pprint(build_lookups())
