"""
Integration discovery and coordination for the application layer.

Adapters are supplied explicitly when constructing an IntegrationDirectory.
There is no global registry and no backend-specific selection logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Iterable, Mapping

from casita.integrations import (
    Capability,
    Integration,
    ReadRequest,
)
from casita.integrations.base import DomainRecord


@dataclass(frozen=True, slots=True)
class IntegrationFailure:
    """Describe one adapter failure without leaking its exception type."""

    integration_key: str
    capability: Capability
    message: str


@dataclass(frozen=True, slots=True)
class CapabilityRead:
    """Collect normalized records returned for one capability."""

    capability: Capability
    records: tuple[DomainRecord, ...]
    refreshed_at: datetime | None
    failures: tuple[IntegrationFailure, ...] = ()


class IntegrationDirectory:
    """
    Discover injected integrations by capability and ownership.

    The optional owners mapping selects and orders integrations for a
    capability. When ownership is not configured, every integration declaring
    that capability contributes in registration order.
    """

    def __init__(
        self,
        integrations: Iterable[Integration],
        owners: Mapping[Capability, tuple[str, ...]] | None = None,
    ) -> None:
        installed = tuple(integrations)
        by_key: dict[str, Integration] = {}

        for integration in installed:
            raw_key = integration.descriptor.key
            key = raw_key.strip()

            if key == "":
                raise ValueError(
                    "Integration descriptor keys cannot be blank."
                )

            if key != raw_key:
                raise ValueError(
                    "Integration descriptor keys cannot contain "
                    "surrounding whitespace."
                )

            if key in by_key:
                raise ValueError(
                    f"Integration key {key!r} is registered more than once."
                )

            by_key[key] = integration

        configured_owners = dict(owners or {})

        for capability, owner_keys in configured_owners.items():
            if not owner_keys:
                raise ValueError(
                    f"Capability {capability.value!r} has no configured owner."
                )

            for owner_key in owner_keys:
                integration = by_key.get(owner_key)

                if integration is None:
                    raise ValueError(
                        f"Capability {capability.value!r} references "
                        f"unknown integration {owner_key!r}."
                    )

                if capability not in integration.descriptor.capabilities:
                    raise ValueError(
                        f"Integration {owner_key!r} does not declare "
                        f"capability {capability.value!r}."
                    )

        self._integrations = installed
        self._by_key = MappingProxyType(by_key)
        self._owners = MappingProxyType(configured_owners)

    @property
    def integrations(self) -> tuple[Integration, ...]:
        """Return all injected integrations in stable registration order."""

        return self._integrations

    def integrations_for(
        self,
        capability: Capability,
    ) -> tuple[Integration, ...]:
        """Return integrations selected to provide one capability."""

        owner_keys = self._owners.get(capability)

        if owner_keys is not None:
            return tuple(
                self._by_key[owner_key]
                for owner_key in owner_keys
            )

        return tuple(
            integration
            for integration in self._integrations
            if capability in integration.descriptor.capabilities
        )

    def read(
        self,
        household_id: str,
        capability: Capability,
        *,
        since: datetime | None = None,
    ) -> CapabilityRead:
        """Read and combine normalized records from selected integrations."""

        records: list[DomainRecord] = []
        refreshed_at: datetime | None = None
        failures: list[IntegrationFailure] = []
        request = ReadRequest(
            household_id=household_id,
            capabilities=frozenset({capability}),
            since=since,
        )

        for integration in self.integrations_for(capability):
            key = integration.descriptor.key

            try:
                snapshot = integration.read(request)

                if snapshot.integration_key != key:
                    raise ValueError(
                        "Integration snapshot key does not match "
                        f"descriptor key {key!r}."
                    )

                if snapshot.household_id != household_id:
                    raise ValueError(
                        "Integration snapshot household does not match "
                        f"request {household_id!r}."
                    )

                for capability_data in snapshot.data:
                    if capability_data.capability != capability:
                        continue

                    records.extend(capability_data.records)

                    if (
                        refreshed_at is None
                        or capability_data.refreshed_at > refreshed_at
                    ):
                        refreshed_at = capability_data.refreshed_at
            except Exception as error:
                failures.append(
                    IntegrationFailure(
                        integration_key=key,
                        capability=capability,
                        message=str(error) or error.__class__.__name__,
                    )
                )

        return CapabilityRead(
            capability=capability,
            records=tuple(records),
            refreshed_at=refreshed_at,
            failures=tuple(failures),
        )
