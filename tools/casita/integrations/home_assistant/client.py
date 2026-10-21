"""Bounded authenticated HTTP client for Home Assistant's REST API."""

from __future__ import annotations

from typing import Any

import requests


class HomeAssistantApiError(RuntimeError):
    """Represent a safe Home Assistant transport failure."""


class HomeAssistantAuthenticationError(HomeAssistantApiError):
    """Represent rejected Home Assistant credentials."""


class HomeAssistantResponseError(HomeAssistantApiError):
    """Represent a malformed or unexpected Home Assistant response."""


class HomeAssistantApiClient:
    """Perform read-only authenticated requests without exposing credentials."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 10,
        session: Any | None = None,
    ) -> None:
        self._base_url = str(base_url).rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        self._timeout = float(timeout)
        self._session = session or requests.Session()

    def get_root(self) -> dict[str, Any]:
        """Read the authenticated API root for health reporting."""

        payload = self._get("/")
        if not isinstance(payload, dict):
            raise HomeAssistantResponseError(
                "Home Assistant returned an invalid health response."
            )
        return payload

    def get_states(self) -> list[dict[str, Any]]:
        """Read current entity states."""

        payload = self._get("/states")
        if not isinstance(payload, list):
            raise HomeAssistantResponseError(
                "Home Assistant returned an invalid states response."
            )
        return payload

    def _get(self, endpoint: str) -> Any:
        try:
            response = self._session.get(
                f"{self._base_url}/api{endpoint}",
                headers=self._headers,
                timeout=self._timeout,
            )
        except requests.Timeout as error:
            raise TimeoutError("Home Assistant request timed out.") from error
        except requests.RequestException as error:
            raise HomeAssistantApiError(
                "Home Assistant could not be reached."
            ) from error

        if response.status_code in (401, 403):
            raise HomeAssistantAuthenticationError(
                "Home Assistant authentication failed."
            )
        if not 200 <= response.status_code < 300:
            raise HomeAssistantApiError(
                "Home Assistant returned an unsuccessful response."
            )

        try:
            return response.json()
        except (TypeError, ValueError) as error:
            raise HomeAssistantResponseError(
                "Home Assistant returned invalid JSON."
            ) from error
