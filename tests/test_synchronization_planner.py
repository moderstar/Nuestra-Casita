"""Tests for structured synchronization planning."""

from datetime import datetime, timezone
from unittest import TestCase

from casita.application import (
    IntegrationDirectory,
    SynchronizationPlanner,
)
from casita.integrations import (
    ApplyResult,
    HealthStatus,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationSnapshot,
    PlannedChange,
    SyncAction,
    SynchronizationPlan,
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
        return ApplyResult(
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
