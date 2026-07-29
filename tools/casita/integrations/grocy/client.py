"""Reusable authenticated HTTP client for the Grocy integration."""

import requests


class GrocyApiClient:
    """Perform authenticated requests against one Grocy API instance."""

    def __init__(self, base_url, api_key):
        self.base_url = str(base_url).rstrip("/")
        self.headers = {
            "GROCY-API-KEY": str(api_key),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get(self, endpoint):
        """Perform a GET request."""

        response = requests.get(
            f"{self.base_url}/api{endpoint}",
            headers=self.headers,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    def post(self, endpoint, payload):
        """Perform a POST request."""

        response = requests.post(
            f"{self.base_url}/api{endpoint}",
            headers=self.headers,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()

        if response.text:
            return response.json()

        return None

    def put(self, endpoint, payload):
        """Perform a PUT request."""

        response = requests.put(
            f"{self.base_url}/api{endpoint}",
            headers=self.headers,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()

        if response.text:
            return response.json()

        return None

    def delete(self, endpoint):
        """Perform a DELETE request."""

        response = requests.delete(
            f"{self.base_url}/api{endpoint}",
            headers=self.headers,
            timeout=10,
        )

        response.raise_for_status()

        if response.text:
            return response.json()

        return None
