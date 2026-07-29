"""Tests for structured synchronization planning."""

from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from unittest import TestCase

from casita.application import (
    CatalogApplicationService,
    CatalogExecutionResult,
    CatalogOperationResult,
    CatalogPlan,
    IntegrationDirectory,
    IntegrationCatalogExecutor,
    IntegrationCatalogPlanner,
    SynchronizationApplicationService,
)
from casita.integrations import (
    HealthStatus,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationSnapshot,
    PlannedChange,
    SyncAction,
    SynchronizationPlan,
    SynchronizationResult,
)


class FakeSynchronizingIntegration:
    """Return structured plans without depending on a concrete backend."""

    descriptor = IntegrationDescriptor(
        key="fake",
        display_name="Fake",
        capabilities=frozenset(),
    )

    def health(self):
        return IntegrationHealth(
            integration_key="fake",
            status=HealthStatus.HEALTHY,
            checked_at=datetime.now(timezone.utc),
        )

    def read(self, request):
        return IntegrationSnapshot(
            integration_key="fake",
            household_id=request.household_id,
            generated_at=datetime.now(timezone.utc),
            data=(),
        )

    def plan(self, request):
        return SynchronizationPlan(
            integration_key="fake",
            resource=request.resource,
            generated_at=datetime.now(timezone.utc),
            changes=(
                PlannedChange(
                    identity="milk",
                    display_name="Milk",
                    action=SyncAction.MATCH,
                ),
            ),
        )

    def apply(self, plan):
        return SynchronizationResult(
            integration_key="fake",
            resource=plan.resource,
            created=0,
            updated=0,
            matched=1,
            completed_at=datetime.now(timezone.utc),
        )


class CatalogPlannerTests(TestCase):
    def test_returns_structured_integration_plan(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        planner = IntegrationCatalogPlanner(directory, owner="fake")

        plan = planner.plan("household", "products")

        self.assertIsInstance(plan, CatalogPlan)
        self.assertEqual(plan.integration_key, "fake")
        self.assertEqual(plan.resource, "products")
        self.assertEqual(plan.changes[0].action, SyncAction.MATCH)

    def test_rejects_mismatched_plan_resource(self):
        class MismatchedIntegration(FakeSynchronizingIntegration):
            def plan(self, request):
                plan = super().plan(request)
                return SynchronizationPlan(
                    integration_key=plan.integration_key,
                    resource="wrong-resource",
                    generated_at=plan.generated_at,
                    changes=plan.changes,
                )

        directory = IntegrationDirectory((MismatchedIntegration(),))
        planner = IntegrationCatalogPlanner(directory, owner="fake")

        with self.assertRaisesRegex(
            ValueError,
            "plan resource does not match",
        ):
            planner.plan("household", "products")

    def test_rejects_blank_catalog_request(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        planner = IntegrationCatalogPlanner(directory, owner="fake")

        with self.assertRaisesRegex(ValueError, "household ID"):
            planner.plan("", "products")

        with self.assertRaisesRegex(ValueError, "resource"):
            planner.plan("household", " ")


class CatalogExecutorTests(TestCase):
    def test_returns_structured_execution_result(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        planner = IntegrationCatalogPlanner(directory, owner="fake")
        executor = IntegrationCatalogExecutor(directory, owner="fake")
        plan = planner.plan("household", "products")

        result = executor.execute(plan)

        self.assertIsInstance(result, CatalogExecutionResult)
        self.assertEqual(result.integration_key, "fake")
        self.assertEqual(result.resource, "products")
        self.assertEqual(result.matched, 1)

    def test_rejects_plan_for_another_integration(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        executor = IntegrationCatalogExecutor(directory, owner="fake")
        integration_plan = SynchronizationPlan(
            integration_key="another",
            resource="products",
            generated_at=datetime.now(timezone.utc),
            changes=(),
        )
        plan = CatalogPlan(
            household_id="household",
            integration_key="another",
            resource="products",
            generated_at=integration_plan.generated_at,
            operations=(),
            integration_plan=integration_plan,
        )

        with self.assertRaisesRegex(
            ValueError,
            "plan integration key does not match",
        ):
            executor.execute(plan)

    def test_rejects_result_counts_that_do_not_match_plan(self):
        class IncorrectResultIntegration(FakeSynchronizingIntegration):
            def apply(self, plan):
                return SynchronizationResult(
                    integration_key="fake",
                    resource=plan.resource,
                    created=1,
                    updated=0,
                    matched=0,
                    completed_at=datetime.now(timezone.utc),
                )

        directory = IntegrationDirectory((IncorrectResultIntegration(),))
        planner = IntegrationCatalogPlanner(directory, owner="fake")
        executor = IntegrationCatalogExecutor(directory, owner="fake")
        plan = planner.plan("household", "products")

        with self.assertRaisesRegex(
            ValueError,
            "result counts do not match",
        ):
            executor.execute(plan)

    def test_planner_and_executor_are_presentation_neutral(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        planner = IntegrationCatalogPlanner(directory, owner="fake")
        executor = IntegrationCatalogExecutor(directory, owner="fake")
        output = StringIO()

        with redirect_stdout(output):
            plan = planner.plan("household", "products")
            executor.execute(plan)

        self.assertEqual(output.getvalue(), "")


class SynchronizationApplicationServiceTests(TestCase):
    def test_orchestrates_all_resources_in_dependency_order(self):
        integration = FakeSynchronizingIntegration()
        directory = IntegrationDirectory((integration,))
        catalogs = CatalogApplicationService(
            IntegrationCatalogPlanner(directory, owner="fake"),
            IntegrationCatalogExecutor(directory, owner="fake"),
            resources=("groups", "products"),
        )
        service = SynchronizationApplicationService(
            catalogs,
            resources=("all", "groups", "products"),
            resource_order=("groups", "products"),
        )
        announced = []
        planned = []
        applied = []

        run = service.synchronize(
            "household",
            "all",
            apply=True,
            on_resource=announced.append,
            on_plan=lambda plan: planned.append(plan.resource),
            on_result=lambda result: applied.append(result.resource),
        )

        self.assertTrue(run.applied)
        self.assertEqual(
            tuple(plan.resource for plan in run.plans),
            ("groups", "products"),
        )
        self.assertEqual(
            tuple(result.resource for result in run.results),
            ("groups", "products"),
        )
        self.assertEqual(announced, ["groups", "products"])
        self.assertEqual(planned, ["groups", "products"])
        self.assertEqual(applied, ["groups", "products"])

    def test_dry_run_plans_without_executing(self):
        class ApplyForbiddenIntegration(FakeSynchronizingIntegration):
            def apply(self, plan):
                raise AssertionError("Dry-run attempted execution")

        directory = IntegrationDirectory(
            (ApplyForbiddenIntegration(),)
        )
        catalogs = CatalogApplicationService(
            IntegrationCatalogPlanner(directory, owner="fake"),
            IntegrationCatalogExecutor(directory, owner="fake"),
            resources=("products",),
        )
        service = SynchronizationApplicationService(
            catalogs,
            resources=("all", "products"),
            resource_order=("products",),
        )

        run = service.synchronize(
            "household",
            "products",
            apply=False,
        )

        self.assertFalse(run.applied)
        self.assertEqual(len(run.plans), 1)
        self.assertEqual(run.results, ())


class CatalogApplicationServiceTests(TestCase):
    def test_returns_structured_catalog_operation_result(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        service = CatalogApplicationService(
            IntegrationCatalogPlanner(directory, owner="fake"),
            IntegrationCatalogExecutor(directory, owner="fake"),
            resources=("products",),
        )

        operation = service.synchronize(
            "household",
            "products",
            apply=True,
        )

        self.assertIsInstance(operation, CatalogOperationResult)
        self.assertEqual(operation.resource, "products")
        self.assertEqual(operation.plan.resource, "products")
        self.assertEqual(operation.execution.resource, "products")
        self.assertTrue(operation.applied)

    def test_rejects_unknown_catalog_resource(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        service = CatalogApplicationService(
            IntegrationCatalogPlanner(directory, owner="fake"),
            IntegrationCatalogExecutor(directory, owner="fake"),
            resources=("products",),
        )

        with self.assertRaisesRegex(
            ValueError,
            "Unknown catalog resource",
        ):
            service.synchronize("household", "unknown")
