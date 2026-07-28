from casita.grocy import get

lookups = {
    "locations": {},
    "units": {},
    "groups": {},
    "stores": {},
}

for item in get("/objects/locations"):
    lookups["locations"][item["name"]] = item["id"]

for item in get("/objects/quantity_units"):
    lookups["units"][item["name"]] = item["id"]

for item in get("/objects/product_groups"):
    lookups["groups"][item["name"]] = item["id"]

for item in get("/objects/shopping_locations"):
    lookups["stores"][item["name"]] = item["id"]

if __name__ == "__main__":
    from pprint import pprint
    pprint(lookups)
