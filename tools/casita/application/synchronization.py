"""Structured synchronization orchestration for application services."""

from __future__ import annotations

from casita.application.coordination import IntegrationDirectory
from casita.integrations import (
    SynchronizationPlan,
    SynchronizingIntegration,
    SyncRequest,
)


class SynchronizationPlanner:
    """Request and validate structured plans from an owning integration."""

    def __init__(
        self,
        integrations: IntegrationDirectory,
        *,
        owner: str,
    ) -> None:
        self._integrations = integrations
        self._owner = owner

    def plan(
        self,
        household_id: str,
        resource: str,
    ) -> SynchronizationPlan:
        """Build one backend-neutral synchronization plan."""

        integration = self._integrations.get(self._owner)

        if not isinstance(integration, SynchronizingIntegration):
            raise RuntimeError(
                f"Integration {self._owner!r} does not support "
                "structured synchronization planning."
            )

        request = SyncRequest(
            household_id=household_id,
            resource=resource,
        )
        plan = integration.plan(request)

        if plan.integration_key != integration.descriptor.key:
            raise ValueError(
                "Synchronization plan integration key does not match "
                f"descriptor key {integration.descriptor.key!r}."
            )

        if plan.resource != resource:
            raise ValueError(
                "Synchronization plan resource does not match "
                f"request {resource!r}."
            )

        return plan
