"""Tests for presentation-free native synchronization operations."""

from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from casita.apply import apply_plan
from casita.sync import plan_registered_resource


class NativeSynchronizationSilenceTests(TestCase):
    @patch("casita.sync.build_resource_plan")
    @patch("casita.sync.load_grocy")
    @patch("casita.sync.load_catalog")
    @patch("casita.sync.get_resource")
    def test_native_planner_produces_no_terminal_output(
        self,
        get_resource,
        load_catalog,
        load_grocy,
        build_resource_plan,
    ):
        get_resource.return_value = {
            "plural_name": "products",
            "requires_lookups": False,
        }
        load_catalog.return_value = [{"name": "Milk"}]
        load_grocy.return_value = []
        build_resource_plan.return_value = {
            "create": [{"name": "Milk"}],
            "update": [],
            "match": [],
        }
        output = StringIO()

        with redirect_stdout(output):
            _, plan = plan_registered_resource("products")

        self.assertEqual(output.getvalue(), "")
        self.assertEqual(plan["_metadata"]["catalog_count"], 1)

    def test_native_applier_produces_no_terminal_output(self):
        resource = {
            "plural_name": "products",
            "requires_lookups": False,
        }
        plan = {
            "create": [],
            "update": [],
            "match": [{"name": "Milk"}],
        }
        output = StringIO()

        with redirect_stdout(output):
            result = apply_plan(resource, plan)

        self.assertEqual(output.getvalue(), "")
        self.assertEqual(result["matched"], 1)
