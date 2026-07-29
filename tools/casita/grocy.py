import json
import os

import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv("/opt/Nuestra-Casita/.env")

BASE_URL = os.getenv("GROCY_URL")
API_KEY = os.getenv("GROCY_API_KEY")

if not BASE_URL or not API_KEY:
    raise RuntimeError("Missing GROCY_URL or GROCY_API_KEY in .env")

HEADERS = {
    "GROCY-API-KEY": API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def _debug_response(response, payload=None):
    """Print detailed request/response information when Grocy returns an error."""

    if response.ok:
        return

    print("\n" + "=" * 80)
    print("GROCY API ERROR")
    print("=" * 80)
    print(f"Status : {response.status_code}")
    print(f"Method : {response.request.method}")
    print(f"URL    : {response.request.url}")

    if payload is not None:
        print("\nPayload:")
        print(json.dumps(payload, indent=4, sort_keys=True))

    print("\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"{key}: {value}")

    print("\nResponse Body:")
    if response.text:
        print(response.text)
    else:
        print("<empty>")

    print("=" * 80 + "\n")

    response.raise_for_status()


def get(endpoint):
    """Perform a GET request."""

    response = requests.get(
        f"{BASE_URL}/api{endpoint}",
        headers=HEADERS,
        timeout=10,
    )

    _debug_response(response)

    return response.json()


def post(endpoint, payload):
    """Perform a POST request."""

    response = requests.post(
        f"{BASE_URL}/api{endpoint}",
        headers=HEADERS,
        json=payload,
        timeout=10,
    )

    _debug_response(response, payload)

    if response.text:
        return response.json()

    return None


def put(endpoint, payload):
    """Perform a PUT request."""

    response = requests.put(
        f"{BASE_URL}/api{endpoint}",
        headers=HEADERS,
        json=payload,
        timeout=10,
    )

    _debug_response(response, payload)

    if response.text:
        return response.json()

    return None


def delete(endpoint):
    """Perform a DELETE request."""

    response = requests.delete(
        f"{BASE_URL}/api{endpoint}",
        headers=HEADERS,
        timeout=10,
    )

    _debug_response(response)

    if response.text:
        return response.json()

    return None
