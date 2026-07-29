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


def get(endpoint):
    """Perform a GET request."""

    response = requests.get(
        f"{BASE_URL}/api{endpoint}",
        headers=HEADERS,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def post(endpoint, payload):
    """Perform a POST request."""

    response = requests.post(
        f"{BASE_URL}/api{endpoint}",
        headers=HEADERS,
        json=payload,
        timeout=10,
    )

    response.raise_for_status()

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

    response.raise_for_status()

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

    response.raise_for_status()

    if response.text:
        return response.json()

    return None
