import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/opt/Nuestra-Casita/.env")

GROCY_URL = os.getenv("GROCY_URL")
GROCY_API_KEY = os.getenv("GROCY_API_KEY")

if not GROCY_URL or not GROCY_API_KEY:
    raise RuntimeError("Missing GROCY_URL or GROCY_API_KEY in .env")

headers = {
    "GROCY-API-KEY": GROCY_API_KEY,
    "Accept": "application/json",
}

url = f"{GROCY_URL}/api/system/info"

response = requests.get(url, headers=headers, timeout=10)

print(f"Status Code: {response.status_code}")

if response.ok:
    print("✅ Connected to Grocy!")
    print(response.json())
else:
    print(response.text)
