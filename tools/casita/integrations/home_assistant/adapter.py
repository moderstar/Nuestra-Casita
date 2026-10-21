"""Normalize allowlisted Home Assistant entity states."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Protocol

from casita.domain import Device, DeviceState, SourceReference
from casita.integrations import (
    Capability,
    CapabilityData,
    HealthStatus,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationSnapshot,
    ReadRequest,
)


class HomeAssistantReader(Protocol):
    """Minimal read-only Home Assistant transport used by the adapter."""

    def get_root(self) -> dict[str, Any]:
        """Read authenticated API health information."""

    def get_states(self) -> list[dict[str, Any]]:
        """Read current entity states."""


DISPLAY_ATTRIBUTES = (
    "device_class",
    "battery_level",
    "brightness",
    "percentage",
    "current_temperature",
    "temperature",
    "humidity",
    "hvac_action",
    "mode",
)


class HomeAssistantReadAdapter:
    """Provide allowlisted Home Assistant states as household devices."""

    descriptor = IntegrationDescriptor(
        key="home-assistant",
        display_name="Home Assistant",
        capabilities=frozenset({Capability.DEVICES}),
    )

    def __init__(
        self,
        client: HomeAssistantReader,
        *,
        entity_ids: tuple[str, ...],
    ) -> None:
        self._client = client
        self._entity_ids = entity_ids

    def health(self) -> IntegrationHealth:
        """Report authenticated API availability without leaking details."""

        checked_at = datetime.now(timezone.utc)
        try:
            self._client.get_root()
        except Exception:
            return IntegrationHealth(
                integration_key=self.descriptor.key,
                status=HealthStatus.UNAVAILABLE,
                checked_at=checked_at,
                message="Home Assistant is unavailable.",
            )
        return IntegrationHealth(
            integration_key=self.descriptor.key,
            status=HealthStatus.HEALTHY,
            checked_at=checked_at,
        )

    def read(self, request: ReadRequest) -> IntegrationSnapshot:
        """Read and normalize only explicitly allowlisted entity states."""

        refreshed_at = datetime.now(timezone.utc)
        records: tuple[Device, ...] = ()
        if Capability.DEVICES in request.capabilities and self._entity_ids:
            records = self._map_states(
                request.household_id,
                self._client.get_states(),
            )
        data = (
            CapabilityData(Capability.DEVICES, records, refreshed_at),
        ) if Capability.DEVICES in request.capabilities else ()
        return IntegrationSnapshot(
            integration_key=self.descriptor.key,
            household_id=request.household_id,
            generated_at=refreshed_at,
            data=data,
        )

    def _map_states(
        self,
        household_id: str,
        rows: list[dict[str, Any]],
    ) -> tuple[Device, ...]:
        by_entity_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Home Assistant returned a malformed entity state.")
            entity_id = row.get("entity_id")
            raw_state = row.get("state")
            attributes = row.get("attributes", {})
            if (
                not isinstance(entity_id, str)
                or not isinstance(raw_state, str)
                or not isinstance(attributes, dict)
            ):
                raise ValueError("Home Assistant returned a malformed entity state.")
            if entity_id in by_entity_id:
                raise ValueError("Home Assistant returned a duplicate entity state.")
            by_entity_id[entity_id] = row

        return tuple(
            self._device(household_id, entity_id, by_entity_id.get(entity_id))
            for entity_id in self._entity_ids
        )

    @staticmethod
    def _device(
        household_id: str,
        entity_id: str,
        row: dict[str, Any] | None,
    ) -> Device:
        domain, object_id = entity_id.split(".", 1)
        raw_state = "unavailable" if row is None else str(row["state"])
        raw_attributes = {} if row is None else row["attributes"]
        if raw_state == "unavailable":
            availability = DeviceState.UNAVAILABLE
        elif raw_state == "unknown":
            availability = DeviceState.UNKNOWN
        else:
            availability = DeviceState.AVAILABLE
        name = str(raw_attributes.get("friendly_name") or object_id)
        unit = str(raw_attributes.get("unit_of_measurement") or "")
        attributes = tuple(
            (key, str(raw_attributes[key]))
            for key in DISPLAY_ATTRIBUTES
            if key in raw_attributes
            and isinstance(raw_attributes[key], (str, int, float, bool))
        )
        identity = sha256(entity_id.encode()).hexdigest()[:20]
        return Device(
            id=f"home-device-{identity}",
            household_id=household_id,
            name=name,
            kind=domain,
            state=availability,
            value=raw_state,
            unit=unit,
            attributes=attributes,
            source_references=(
                SourceReference("home-assistant", entity_id, domain),
            ),
        )
