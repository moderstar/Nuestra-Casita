"""Home Assistant read-only integration."""

from casita.integrations.home_assistant.adapter import HomeAssistantReadAdapter
from casita.integrations.home_assistant.client import (
    HomeAssistantApiClient,
    HomeAssistantApiError,
    HomeAssistantAuthenticationError,
    HomeAssistantResponseError,
)

__all__ = [
    "HomeAssistantApiClient",
    "HomeAssistantApiError",
    "HomeAssistantAuthenticationError",
    "HomeAssistantReadAdapter",
    "HomeAssistantResponseError",
]
