"""Backend-neutral planning and execution for declarative catalogs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from casita.application.coordination import IntegrationDirectory
from casita.integrations import (
    AppliedChange,
    FieldDifference,
    SyncAction,
    SyncRequest,
    SynchronizationPlan,
    SynchronizationResult,
    SynchronizingIntegration,
)


@dataclass(frozen=True, slots=True)
class CatalogOperation:
    """Describe one backend-neutral catalog planning decision."""

    identity: str
    display_name: str
    action: SyncAction
    differences: tuple[FieldDifference, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogPlan:
    """Represent one validated catalog plan without backend payloads."""

    household_id: str
    integration_key: str
    resource: str
    generated_at: datetime
    operations: tuple[CatalogOperation, ...]
    resource_label: str = ""
    catalog_count: int = 0
    backend_count: int = 0
    lookups_loaded: bool = False
    integration_plan: SynchronizationPlan | None = None

    @property
    def changes(self) -> tuple[CatalogOperation, ...]:
        """Expose operations under the established presentation name."""

        return self.operations


@dataclass(frozen=True, slots=True)
class CatalogExecutionResult:
    """Return the structured result of executing one catalog plan."""

    integration_key: str
    resource: str
    created: int
    updated: int
    matched: int
    completed_at: datetime
    changes: tuple[AppliedChange, ...] = ()
    resource_label: str = ""
    lookups_loaded: bool = False


@dataclass(frozen=True, slots=True)
class CatalogOperationResult:
    """Return one catalog plan and its optional execution result."""

    resource: str
    plan: CatalogPlan
    execution: CatalogExecutionResult | None
    applied: bool


class CatalogPlanner(Protocol):
    """Build structured plans for catalog resources."""

    def plan(
        self,
        household_id: str,
        resource: str,
    ) -> CatalogPlan:
        """Build one catalog plan."""


class CatalogExecutor(Protocol):
    """Execute structured catalog plans."""

    def execute(
        self,
        plan: CatalogPlan,
    ) -> CatalogExecutionResult:
        """Execute one catalog plan."""


class IntegrationCatalogPlanner:
    """Plan catalogs through a backend-neutral integration contract."""

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
    ) -> CatalogPlan:
        """Validate a request and return a structured catalog plan."""

        if not str(household_id).strip():
            raise ValueError("Catalog household ID cannot be blank.")

        if not str(resource).strip():
            raise ValueError("Catalog resource cannot be blank.")

        integration = self._integrations.get(self._owner)

        if not isinstance(integration, SynchronizingIntegration):
            raise RuntimeError(
                f"Integration {self._owner!r} does not support "
                "structured catalog planning."
            )

        integration_plan = integration.plan(
            SyncRequest(
                household_id=household_id,
                resource=resource,
            )
        )

        if integration_plan.integration_key != integration.descriptor.key:
            raise ValueError(
                "Catalog plan integration key does not match "
                f"descriptor key {integration.descriptor.key!r}."
            )

        if integration_plan.resource != resource:
            raise ValueError(
                "Catalog plan resource does not match "
                f"request {resource!r}."
            )

        return CatalogPlan(
            household_id=household_id,
            integration_key=integration_plan.integration_key,
            resource=integration_plan.resource,
            generated_at=integration_plan.generated_at,
            operations=tuple(
                CatalogOperation(
                    identity=change.identity,
                    display_name=change.display_name,
                    action=change.action,
                    differences=change.differences,
                )
                for change in integration_plan.changes
            ),
            resource_label=integration_plan.resource_label,
            catalog_count=integration_plan.catalog_count,
            backend_count=integration_plan.backend_count,
            lookups_loaded=integration_plan.lookups_loaded,
            integration_plan=integration_plan,
        )


class IntegrationCatalogExecutor:
    """Execute catalog plans through a backend-neutral integration contract."""

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
        plan: CatalogPlan,
    ) -> CatalogExecutionResult:
        """Apply and validate one structured catalog plan."""

        integration = self._integrations.get(self._owner)

        if not isinstance(integration, SynchronizingIntegration):
            raise RuntimeError(
                f"Integration {self._owner!r} does not support "
                "structured catalog execution."
            )

        if plan.integration_key != integration.descriptor.key:
            raise ValueError(
                "Catalog plan integration key does not match "
                f"descriptor key {integration.descriptor.key!r}."
            )

        if plan.integration_plan is None:
            raise ValueError("Catalog plan has no integration plan.")

        result = integration.apply(plan.integration_plan)

        if result.integration_key != plan.integration_key:
            raise ValueError(
                "Catalog result integration key does not match "
                f"plan key {plan.integration_key!r}."
            )

        if result.resource != plan.resource:
            raise ValueError(
                "Catalog result resource does not match "
                f"plan resource {plan.resource!r}."
            )

        expected = {
            action: sum(
                operation.action == action
                for operation in plan.operations
            )
            for action in SyncAction
        }
        actual = {
            SyncAction.CREATE: result.created,
            SyncAction.UPDATE: result.updated,
            SyncAction.MATCH: result.matched,
        }

        if actual != expected:
            raise ValueError("Catalog result counts do not match the plan.")

        return CatalogExecutionResult(
            integration_key=result.integration_key,
            resource=result.resource,
            created=result.created,
            updated=result.updated,
            matched=result.matched,
            completed_at=result.completed_at,
            changes=result.changes,
            resource_label=result.resource_label,
            lookups_loaded=result.lookups_loaded,
        )


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
        on_plan: Callable[[CatalogPlan], None] | None = None,
        on_result: Callable[[CatalogExecutionResult], None] | None = None,
    ) -> CatalogOperationResult:
        """Plan and optionally execute one validated catalog resource."""

        if resource not in self._resources:
            raise ValueError(f"Unknown catalog resource {resource!r}.")

        plan = self._planner.plan(household_id, resource)

        if on_plan is not None:
            on_plan(plan)

        execution = self._executor.execute(plan) if apply else None

        if execution is not None and on_result is not None:
            on_result(execution)

        return CatalogOperationResult(
            resource=resource,
            plan=plan,
            execution=execution,
            applied=apply,
        )
