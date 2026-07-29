"""Grocy read adapter for the Nuestra Casita integration contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from casita.integrations import (
    Capability,
    CapabilityData,
    HealthStatus,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationSnapshot,
    ReadRequest,
)
from casita.integrations.grocy.client import GrocyApiClient
from casita.integrations.grocy.mapping import (
    map_chores,
    map_inventory,
    map_recipes,
    map_shopping_lists,
    rows_by_id,
)


class GrocyReader(Protocol):
    """Minimal Grocy transport required by the read adapter."""

    def get(self, endpoint: str) -> Any:
        """Return one decoded Grocy API response."""


class GrocyReadAdapter:
    """Translate Grocy 4.6 API responses into household domain models."""

    descriptor = IntegrationDescriptor(
        key="grocy",
        display_name="Grocy",
        capabilities=frozenset(
            {
                Capability.SHOPPING,
                Capability.INVENTORY,
                Capability.RECIPES,
                Capability.CHORES,
            }
        ),
        version="4.6",
    )

    def __init__(
        self,
        client: GrocyReader,
        *,
        timezone_name: str = "UTC",
    ) -> None:
        self._client = client
        self._timezone = ZoneInfo(timezone_name)

    @classmethod
    def from_credentials(
        cls,
        base_url: str,
        api_key: str,
        *,
        timezone_name: str = "UTC",
    ) -> GrocyReadAdapter:
        """Construct an adapter with the shared Grocy HTTP client."""

        return cls(
            GrocyApiClient(base_url, api_key),
            timezone_name=timezone_name,
        )

    def health(self) -> IntegrationHealth:
        """Check whether the configured Grocy API is reachable."""

        checked_at = datetime.now(timezone.utc)

        try:
            self._client.get("/system/info")
        except Exception as error:
            return IntegrationHealth(
                integration_key=self.descriptor.key,
                status=HealthStatus.UNAVAILABLE,
                checked_at=checked_at,
                message=str(error) or error.__class__.__name__,
            )

        return IntegrationHealth(
            integration_key=self.descriptor.key,
            status=HealthStatus.HEALTHY,
            checked_at=checked_at,
        )

    def read(self, request: ReadRequest) -> IntegrationSnapshot:
        """Read requested capabilities and return normalized domain records."""

        unsupported = request.capabilities - self.descriptor.capabilities

        if unsupported:
            names = ", ".join(
                sorted(capability.value for capability in unsupported)
            )
            raise ValueError(
                f"Grocy does not provide requested capabilities: {names}."
            )

        generated_at = datetime.now(timezone.utc)
        cache: dict[str, list[dict[str, Any]]] = {}

        def rows(endpoint: str) -> list[dict[str, Any]]:
            if endpoint not in cache:
                response = self._client.get(endpoint)

                if not isinstance(response, list):
                    raise ValueError(
                        f"Grocy endpoint {endpoint!r} did not return a list."
                    )

                if not all(isinstance(row, dict) for row in response):
                    raise ValueError(
                        f"Grocy endpoint {endpoint!r} returned an "
                        "invalid record."
                    )

                cache[endpoint] = response

            return cache[endpoint]

        data = []

        for capability in sorted(
            request.capabilities,
            key=lambda item: item.value,
        ):
            if capability == Capability.INVENTORY:
                records = (
                    map_inventory(
                        request.household_id,
                        rows("/stock"),
                        rows_by_id(rows("/objects/quantity_units")),
                        measured_at=generated_at,
                    ),
                )
            elif capability == Capability.SHOPPING:
                records = map_shopping_lists(
                    request.household_id,
                    rows("/objects/shopping_lists"),
                    rows("/objects/shopping_list"),
                    rows_by_id(rows("/objects/products")),
                    rows_by_id(rows("/objects/quantity_units")),
                    self._timezone,
                )
            elif capability == Capability.RECIPES:
                records = map_recipes(
                    request.household_id,
                    rows("/objects/recipes?query[]=type=normal"),
                    rows("/objects/recipes_pos"),
                    rows_by_id(rows("/objects/products")),
                    rows_by_id(rows("/objects/quantity_units")),
                )
            elif capability == Capability.CHORES:
                records = map_chores(
                    request.household_id,
                    rows("/objects/chores"),
                    rows("/chores"),
                    self._timezone,
                )
            else:
                raise AssertionError(
                    f"Unhandled Grocy capability {capability.value!r}."
                )

            data.append(
                CapabilityData(
                    capability=capability,
                    records=records,
                    refreshed_at=generated_at,
                )
            )

        return IntegrationSnapshot(
            integration_key=self.descriptor.key,
            household_id=request.household_id,
            generated_at=generated_at,
            data=tuple(data),
        )
