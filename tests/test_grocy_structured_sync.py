"""Tests for Grocy structured synchronization translation."""

from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase

from casita.integrations import (
    SyncAction,
    SyncRequest,
    SynchronizationPlan,
    SynchronizationResult,
)
from casita.integrations.grocy import GrocyReadAdapter


class FakeClient:
    def get(self, endpoint):
        raise AssertionError(f"Unexpected read from {endpoint}")


class GrocyStructuredSyncTests(TestCase):
    def setUp(self):
        self.applied = []

        def planner(resource_name):
            return (
                {"name": resource_name},
                {
                    "create": [
                        {
                            "name": "Milk",
                            "catalog": {"Product": "Milk"},
                        },
                    ],
                    "update": [],
                    "match": [
                        {
                            "name": "Eggs",
                            "object_id": 2,
                        },
                    ],
                },
            )

        def applier(resource, native_plan):
            self.applied.append((resource, native_plan))
            return {
                "created": 1,
                "updated": 0,
                "matched": 1,
            }

        self.adapter = GrocyReadAdapter(
            FakeClient(),
            sync_planner=planner,
            sync_applier=applier,
        )

    def test_plans_and_applies_structured_grocy_sync(self):
        plan = self.adapter.plan(
            SyncRequest("household", "products")
        )

        self.assertIsInstance(plan, SynchronizationPlan)
        self.assertTrue(plan.plan_id)
        self.assertEqual(
            tuple(change.action for change in plan.changes),
            (SyncAction.CREATE, SyncAction.MATCH),
        )

        result = self.adapter.apply(plan)

        self.assertIsInstance(result, SynchronizationResult)
        self.assertEqual(result.created, 1)
        self.assertEqual(result.matched, 1)
        self.assertEqual(len(self.applied), 1)

    def test_rejects_modified_public_plan(self):
        plan = self.adapter.plan(
            SyncRequest("household", "products")
        )
        modified = SynchronizationPlan(
            integration_key=plan.integration_key,
            resource="locations",
            generated_at=plan.generated_at,
            changes=plan.changes,
            plan_id=plan.plan_id,
        )

        with self.assertRaisesRegex(
            ValueError,
            "not prepared by this Grocy adapter",
        ):
            self.adapter.apply(modified)

    def test_planning_and_applying_produce_no_terminal_output(self):
        output = StringIO()

        with redirect_stdout(output):
            plan = self.adapter.plan(
                SyncRequest("household", "products")
            )
            self.adapter.apply(plan)

        self.assertEqual(output.getvalue(), "")
