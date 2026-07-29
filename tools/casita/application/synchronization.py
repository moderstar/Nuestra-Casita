"""Structured synchronization orchestration for application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from casita.application.catalog import (
    CatalogApplicationService,
    CatalogExecutionResult,
    CatalogPlan,
)


@dataclass(frozen=True, slots=True)
class SynchronizationRun:
    """Collect structured plans and optional execution results."""

    plans: tuple[CatalogPlan, ...]
    results: tuple[CatalogExecutionResult, ...]
    applied: bool


class SynchronizationApplicationService:
    """Orchestrate planning and execution for one or all resources."""

    def __init__(
        self,
        catalogs: CatalogApplicationService,
        *,
        resources: tuple[str, ...],
        resource_order: tuple[str, ...],
        all_resource: str = "all",
    ) -> None:
        self._catalogs = catalogs
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
        on_plan: Callable[[CatalogPlan], None] | None = None,
        on_result: Callable[[CatalogExecutionResult], None] | None = None,
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

            operation = self._catalogs.synchronize(
                household_id,
                resource_name,
                apply=apply,
                on_plan=on_plan,
                on_result=on_result,
            )
            plans.append(operation.plan)

            if operation.execution is not None:
                results.append(operation.execution)

        return SynchronizationRun(
            plans=tuple(plans),
            results=tuple(results),
            applied=apply,
        )
