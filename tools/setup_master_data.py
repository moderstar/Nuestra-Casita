from grocy_api import get
import requests
import os
from dotenv import load_dotenv

load_dotenv("/opt/Nuestra-Casita/.env")

BASE_URL = os.getenv("GROCY_URL")
API_KEY = os.getenv("GROCY_API_KEY")

HEADERS = {
    "GROCY-API-KEY": API_KEY,
    "Content-Type": "application/json",
}

PRODUCT_GROUPS = [
    "Bakery",
    "Beverages",
    "Breakfast",
    "Canned Goods",
    "Condiments",
    "Dairy",
    "Frozen Foods",
    "Grains & Pasta",
    "Household",
    "Laundry",
    "Meat",
    "Paper Goods",
    "Personal Care",
    "Pet Supplies",
    "Produce",
    "Seafood",
    "Snacks",
    "Spices",
]

existing = get("/objects/product_groups")
existing_names = {g["name"] for g in existing}

print()

for group in PRODUCT_GROUPS:

    if group in existing_names:
        print(f"✓ {group}")
        continue

    response = requests.post(
        f"{BASE_URL}/api/objects/product_groups",
        headers=HEADERS,
        json={
            "name": group
        },
    )

    if response.ok:
        print(f"Created: {group}")
    else:
        print(f"Failed: {group}")
        print(response.text)
