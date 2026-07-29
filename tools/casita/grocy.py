import os

from dotenv import load_dotenv

from casita.integrations.grocy.client import GrocyApiClient


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


CLIENT = GrocyApiClient(BASE_URL, API_KEY)


def get(endpoint):
    """Perform a GET request."""

    return CLIENT.get(endpoint)


def post(endpoint, payload):
    """Perform a POST request."""

    return CLIENT.post(endpoint, payload)


def put(endpoint, payload):
    """Perform a PUT request."""

    return CLIENT.put(endpoint, payload)


def delete(endpoint):
    """Perform a DELETE request."""

    return CLIENT.delete(endpoint)
