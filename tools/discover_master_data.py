from grocy_api import get

entities = [
    "product_groups",
    "locations",
    "quantity_units",
    "shopping_locations",
]

for entity in entities:
    print(f"\n===== {entity} =====")

    try:
        data = get(f"/objects/{entity}")

        print(f"Found {len(data)}")

        for row in data:
            print(row)

    except Exception as e:
        print(e)
