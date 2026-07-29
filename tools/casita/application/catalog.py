"""Backend-neutral orchestration for declarative catalog resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from casita.integrations import SynchronizationPlan, SynchronizationResult


class CatalogPlanner(Protocol):
    """Build structured plans for catalog resources."""

    def plan(
        self,
        household_id: str,
        resource: str,
    ) -> SynchronizationPlan:
        """Build one catalog synchronization plan."""


class CatalogExecutor(Protocol):
    """Execute structured catalog plans."""

    def execute(
        self,
        plan: SynchronizationPlan,
    ) -> SynchronizationResult:
        """Execute one catalog synchronization plan."""


@dataclass(frozen=True, slots=True)
class CatalogOperationResult:
    """Return one catalog plan and its optional execution result."""

    resource: str
    plan: SynchronizationPlan
    result: SynchronizationResult | None
    applied: bool


class CatalogApplicationService:
    """Validate and orchestrate one declarative catalog operation."""

    def __init__(
        self,
        planner: CatalogPlanner,
        executor: CatalogExecutor,
        *,
        resources: tuple[str, ...],
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._resources = resources

    @property
    def resources(self) -> tuple[str, ...]:
        """Return the registered declarative catalog resource names."""

        return self._resources

    def synchronize(
        self,
        household_id: str,
        resource: str,
        *,
        apply: bool = False,
        on_plan: Callable[[SynchronizationPlan], None] | None = None,
        on_result: Callable[[SynchronizationResult], None] | None = None,
    ) -> CatalogOperationResult:
        """Plan and optionally execute one validated catalog resource."""

        if resource not in self._resources:
            raise ValueError(f"Unknown catalog resource {resource!r}.")

        plan = self._planner.plan(household_id, resource)

        if on_plan is not None:
            on_plan(plan)

        result = self._executor.execute(plan) if apply else None

        if result is not None and on_result is not None:
            on_result(result)

        return CatalogOperationResult(
            resource=resource,
            plan=plan,
            result=result,
            applied=apply,
        )
