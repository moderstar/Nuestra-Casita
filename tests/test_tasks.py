"""Tests for safe Grocy 4.6 task-definition synchronization."""

import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from casita.apply import apply_plan
from casita.payloads import (
    build_task_create_payload,
    build_task_update_payload,
    parse_task_due_date,
)
from casita.registry import list_sync_resources
from casita.resources.tasks import TASK_RESOURCE
from casita.sync_engine import build_resource_plan, load_grocy


CLI_PATH = Path(__file__).resolve().parents[1] / "tools" / "casita.py"
CLI_SPEC = importlib.util.spec_from_file_location("casita_cli_tasks", CLI_PATH)
CLI = importlib.util.module_from_spec(CLI_SPEC)
assert CLI_SPEC.loader is not None
CLI_SPEC.loader.exec_module(CLI)


LOOKUPS = {
    "task_categories": {"Household": 4, "Maintenance": 5},
    "task_categories_by_id": {4: "Household", 5: "Maintenance"},
}


def task(
    name="Replace water filter",
    description="Kitchen filter",
    due_date="2026-11-01",
    category="Maintenance",
):
    return {
        "Task": name,
        "Description": description,
        "Due Date": due_date,
        "Task Category": category,
    }


def grocy_task(**overrides):
    row = {
        "id": 20,
        "name": "Replace water filter",
        "description": "Kitchen filter",
        "due_date": "2026-11-01",
        "done": 0,
        "done_timestamp": None,
        "category_id": 5,
        "assigned_to_user_id": None,
        "row_created_timestamp": "2026-10-01 10:00:00",
    }
    row.update(overrides)
    return row


class TaskPayloadTests(TestCase):
    def test_builds_definition_only_create_payload(self):
        payload = build_task_create_payload(task(), LOOKUPS)

        self.assertEqual(
            payload,
            {
                "name": "Replace water filter",
                "description": "Kitchen filter",
                "due_date": "2026-11-01",
                "category_id": 5,
            },
        )
        self.assertNotIn("done", payload)
        self.assertNotIn("done_timestamp", payload)
        self.assertNotIn("assigned_to_user_id", payload)

    def test_allows_blank_optional_due_date_and_category(self):
        payload = build_task_create_payload(
            task(due_date="", category=""),
            LOOKUPS,
        )

        self.assertIsNone(payload["due_date"])
        self.assertIsNone(payload["category_id"])

    def test_rejects_missing_task_name(self):
        with self.assertRaisesRegex(ValueError, "cannot be blank"):
            build_task_create_payload(task(name=""), LOOKUPS)

    def test_rejects_invalid_due_date(self):
        for value in ("11/01/2026", "2026-02-30", "tomorrow"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                    parse_task_due_date(value)

    def test_rejects_missing_task_category_reference(self):
        with self.assertRaisesRegex(ValueError, "was not found in Grocy"):
            build_task_create_payload(task(category="Unknown"), LOOKUPS)

    def test_update_rejects_runtime_fields(self):
        for field in (
            "done",
            "done_timestamp",
            "assigned_to_user_id",
            "row_created_timestamp",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "not safely managed"):
                    build_task_update_payload(
                        {
                            "name": "Replace water filter",
                            "changes": [
                                {"api_field": field, "catalog_value": 0}
                            ],
                        }
                    )


class TaskPlanningTests(TestCase):
    def test_cli_parser_exposes_tasks_command(self):
        args = CLI.build_parser(("all", "tasks")).parse_args(
            ["sync", "tasks", "--apply"]
        )

        self.assertEqual(args.sync_command, "tasks")
        self.assertTrue(args.apply)

    def test_dependency_order_follows_task_categories(self):
        resources = list_sync_resources()

        self.assertLess(
            resources.index("task-categories"),
            resources.index("tasks"),
        )

    def test_empty_catalog_preserves_unmanaged_tasks(self):
        plan = build_resource_plan(
            TASK_RESOURCE,
            [],
            [grocy_task()],
            LOOKUPS,
        )

        self.assertEqual(plan, {"create": [], "update": [], "match": []})

    def test_new_task_produces_create(self):
        plan = build_resource_plan(TASK_RESOURCE, [task()], [], LOOKUPS)

        self.assertEqual(len(plan["create"]), 1)

    def test_unchanged_task_is_an_idempotent_match(self):
        plan = build_resource_plan(
            TASK_RESOURCE,
            [task()],
            [grocy_task(due_date="2026-11-01 00:00:00")],
            LOOKUPS,
        )

        self.assertEqual(len(plan["match"]), 1)
        self.assertEqual(plan["create"], [])
        self.assertEqual(plan["update"], [])

    def test_definition_changes_produce_safe_update_only(self):
        plan = build_resource_plan(
            TASK_RESOURCE,
            [task(description="New description", category="Household")],
            [
                grocy_task(
                    done=1,
                    done_timestamp="2026-10-20 09:30:00",
                    assigned_to_user_id=7,
                )
            ],
            LOOKUPS,
        )
        payload = build_task_update_payload(plan["update"][0])

        self.assertEqual(
            payload,
            {"description": "New description", "category_id": 4},
        )
        self.assertNotIn("done", payload)
        self.assertNotIn("done_timestamp", payload)
        self.assertNotIn("assigned_to_user_id", payload)

    def test_completion_activity_differences_are_ignored(self):
        plan = build_resource_plan(
            TASK_RESOURCE,
            [task()],
            [
                grocy_task(
                    done=1,
                    done_timestamp="2026-10-20 09:30:00",
                    assigned_to_user_id=7,
                )
            ],
            LOOKUPS,
        )

        self.assertEqual(len(plan["match"]), 1)

    def test_duplicate_catalog_task_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate name"):
            build_resource_plan(
                TASK_RESOURCE,
                [task(), task(name=" replace WATER filter ")],
                [],
                LOOKUPS,
            )

    def test_ambiguous_grocy_task_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate names"):
            build_resource_plan(
                TASK_RESOURCE,
                [],
                [grocy_task(), grocy_task(id=21, name="replace WATER filter")],
                LOOKUPS,
            )

    @patch("casita.sync_engine.get")
    def test_api_failure_is_propagated(self, get):
        get.side_effect = RuntimeError("Grocy unavailable")

        with self.assertRaisesRegex(RuntimeError, "Grocy unavailable"):
            load_grocy(TASK_RESOURCE)

        get.assert_called_once_with("/objects/tasks")

    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_dry_run_performs_no_writes(self, post, put):
        plan = build_resource_plan(TASK_RESOURCE, [task()], [], LOOKUPS)

        self.assertEqual(len(plan["create"]), 1)
        post.assert_not_called()
        put.assert_not_called()

    @patch("casita.apply.build_lookups", return_value=LOOKUPS)
    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_explicit_apply_preserves_live_activity(
        self,
        post,
        put,
        build_lookups,
    ):
        create_plan = build_resource_plan(TASK_RESOURCE, [task()], [], LOOKUPS)
        apply_plan(TASK_RESOURCE, create_plan)

        post.assert_called_once_with(
            "/objects/tasks",
            {
                "name": "Replace water filter",
                "description": "Kitchen filter",
                "due_date": "2026-11-01",
                "category_id": 5,
            },
        )

        update_plan = build_resource_plan(
            TASK_RESOURCE,
            [task(description="Updated")],
            [
                grocy_task(
                    done=1,
                    done_timestamp="2026-10-20 09:30:00",
                )
            ],
            LOOKUPS,
        )
        apply_plan(TASK_RESOURCE, update_plan)

        put.assert_called_once_with(
            "/objects/tasks/20",
            {"description": "Updated"},
        )
        build_lookups.assert_called()
