import os

from dotenv import load_dotenv

from casita.integrations.grocy.client import GrocyApiClient


# Load environment variables
load_dotenv("/opt/Nuestra-Casita/.env")

BASE_URL = os.getenv("GROCY_URL")
API_KEY = os.getenv("GROCY_API_KEY")

HEADERS = {
    "GROCY-API-KEY": API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json",
}


CLIENT = (
    GrocyApiClient(BASE_URL, API_KEY)
    if BASE_URL and API_KEY
    else None
)


def configure_client(client):
    """Replace the legacy transport with the composition-root client."""

    global CLIENT
    CLIENT = client


def require_client():
    """Return the configured transport or explain how to configure it."""

    if CLIENT is None:
        raise RuntimeError("Missing GROCY_URL or GROCY_API_KEY in .env")

    return CLIENT


def get(endpoint):
    """Perform a GET request."""

    return require_client().get(endpoint)


def post(endpoint, payload):
    """Perform a POST request."""

    return require_client().post(endpoint, payload)


def put(endpoint, payload):
    """Perform a PUT request."""

    return require_client().put(endpoint, payload)


def delete(endpoint):
    """Perform a DELETE request."""

    return require_client().delete(endpoint)
