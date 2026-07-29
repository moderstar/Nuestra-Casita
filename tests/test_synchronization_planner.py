"""Tests for structured synchronization planning."""

from datetime import datetime, timezone
from unittest import TestCase

from casita.application import (
    IntegrationDirectory,
    SynchronizationExecutor,
    SynchronizationPlanner,
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


class SynchronizationPlannerTests(TestCase):
    def test_returns_structured_integration_plan(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        planner = SynchronizationPlanner(directory, owner="fake")

        plan = planner.plan("household", "products")

        self.assertIsInstance(plan, SynchronizationPlan)
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
        planner = SynchronizationPlanner(directory, owner="fake")

        with self.assertRaisesRegex(
            ValueError,
            "plan resource does not match",
        ):
            planner.plan("household", "products")


class SynchronizationExecutorTests(TestCase):
    def test_returns_structured_execution_result(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        planner = SynchronizationPlanner(directory, owner="fake")
        executor = SynchronizationExecutor(directory, owner="fake")
        plan = planner.plan("household", "products")

        result = executor.execute(plan)

        self.assertIsInstance(result, SynchronizationResult)
        self.assertEqual(result.integration_key, "fake")
        self.assertEqual(result.resource, "products")
        self.assertEqual(result.matched, 1)

    def test_rejects_plan_for_another_integration(self):
        directory = IntegrationDirectory(
            (FakeSynchronizingIntegration(),)
        )
        executor = SynchronizationExecutor(directory, owner="fake")
        plan = SynchronizationPlan(
            integration_key="another",
            resource="products",
            generated_at=datetime.now(timezone.utc),
            changes=(),
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
        planner = SynchronizationPlanner(directory, owner="fake")
        executor = SynchronizationExecutor(directory, owner="fake")
        plan = planner.plan("household", "products")

        with self.assertRaisesRegex(
            ValueError,
            "result counts do not match",
        ):
            executor.execute(plan)
