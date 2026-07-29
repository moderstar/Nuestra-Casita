"""Structured synchronization orchestration for application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from casita.application.coordination import IntegrationDirectory
from casita.integrations import (
    SyncAction,
    SynchronizationPlan,
    SynchronizationResult,
    SynchronizingIntegration,
    SyncRequest,
)


@dataclass(frozen=True, slots=True)
class SynchronizationRun:
    """Collect structured plans and optional execution results."""

    plans: tuple[SynchronizationPlan, ...]
    results: tuple[SynchronizationResult, ...]
    applied: bool


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


class SynchronizationExecutor:
    """Execute and validate one structured synchronization plan."""

    def __init__(
        self,
        integrations: IntegrationDirectory,
        *,
        owner: str,
    ) -> None:
        self._integrations = integrations
        self._owner = owner

    def execute(
        self,
        plan: SynchronizationPlan,
    ) -> SynchronizationResult:
        """Apply a plan through its owner and return structured counts."""

        integration = self._integrations.get(self._owner)

        if not isinstance(integration, SynchronizingIntegration):
            raise RuntimeError(
                f"Integration {self._owner!r} does not support "
                "structured synchronization execution."
            )

        if plan.integration_key != integration.descriptor.key:
            raise ValueError(
                "Synchronization plan integration key does not match "
                f"descriptor key {integration.descriptor.key!r}."
            )

        result = integration.apply(plan)

        if result.integration_key != plan.integration_key:
            raise ValueError(
                "Synchronization result integration key does not match "
                f"plan key {plan.integration_key!r}."
            )

        if result.resource != plan.resource:
            raise ValueError(
                "Synchronization result resource does not match "
                f"plan resource {plan.resource!r}."
            )

        expected = {
            SyncAction.CREATE: sum(
                change.action == SyncAction.CREATE
                for change in plan.changes
            ),
            SyncAction.UPDATE: sum(
                change.action == SyncAction.UPDATE
                for change in plan.changes
            ),
            SyncAction.MATCH: sum(
                change.action == SyncAction.MATCH
                for change in plan.changes
            ),
        }
        actual = {
            SyncAction.CREATE: result.created,
            SyncAction.UPDATE: result.updated,
            SyncAction.MATCH: result.matched,
        }

        if actual != expected:
            raise ValueError(
                "Synchronization result counts do not match the plan."
            )

        return result


class SynchronizationApplicationService:
    """Orchestrate planning and execution for one or all resources."""

    def __init__(
        self,
        planner: SynchronizationPlanner,
        executor: SynchronizationExecutor,
        *,
        resources: tuple[str, ...],
        resource_order: tuple[str, ...],
        all_resource: str = "all",
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._resources = resources
        self._resource_order = resource_order
        self._all_resource = all_resource

    @property
    def resources(self) -> tuple[str, ...]:
        """Return every command accepted by the synchronization CLI."""

        return self._resources

    def synchronize(
        self,
        household_id: str,
        resource: str,
        *,
        apply: bool = False,
        on_resource: Callable[[str], None] | None = None,
        on_plan: Callable[[SynchronizationPlan], None] | None = None,
        on_result: Callable[[SynchronizationResult], None] | None = None,
    ) -> SynchronizationRun:
        """Plan and optionally execute selected resources in order."""

        if resource not in self._resources:
            raise ValueError(
                f"Unknown synchronization resource {resource!r}."
            )

        selected = (
            self._resource_order
            if resource == self._all_resource
            else (resource,)
        )
        plans = []
        results = []

        for resource_name in selected:
            if len(selected) > 1 and on_resource is not None:
                on_resource(resource_name)

            plan = self._planner.plan(household_id, resource_name)
            plans.append(plan)

            if on_plan is not None:
                on_plan(plan)

            if apply:
                result = self._executor.execute(plan)
                results.append(result)

                if on_result is not None:
                    on_result(result)

        return SynchronizationRun(
            plans=tuple(plans),
            results=tuple(results),
            applied=apply,
        )
