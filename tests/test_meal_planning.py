"""Tests for conservative Grocy 4.6 meal-planning synchronization."""

import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from casita.apply import apply_plan
from casita.payloads import (
    build_meal_plan_create_payload,
    build_meal_plan_section_create_payload,
    build_meal_plan_update_payload,
)
from casita.registry import list_sync_resources
from casita.resources.meal_plan import MEAL_PLAN_RESOURCE
from casita.resources.meal_plan_sections import MEAL_PLAN_SECTION_RESOURCE
from casita.sync_engine import build_resource_plan, load_grocy


CLI_PATH = Path(__file__).resolve().parents[1] / "tools" / "casita.py"
CLI_SPEC = importlib.util.spec_from_file_location("casita_cli_meals", CLI_PATH)
CLI = importlib.util.module_from_spec(CLI_SPEC)
assert CLI_SPEC.loader is not None
CLI_SPEC.loader.exec_module(CLI)


LOOKUPS = {
    "meal_plan_sections": {"Breakfast": 1, "Dinner": 3},
    "meal_plan_sections_by_id": {1: "Breakfast", 3: "Dinner"},
    "recipes": {"Pancakes": 10, "Tacos": 11},
    "recipes_by_id": {10: "Pancakes", 11: "Tacos"},
    "products": {"Banana": 20, "Milk": 21},
    "products_by_id": {20: "Banana", 21: "Milk"},
    "units": {"Each": 30, "Liter": 31},
    "units_by_id": {30: "Each", 31: "Liter"},
}


def section(name="Dinner", sort_number="30", time="18:00"):
    return {
        "Meal Plan Section": name,
        "Sort Number": sort_number,
        "Time": time,
    }


def recipe_entry(recipe="Tacos", servings="2", **overrides):
    row = {
        "Day": "2026-11-01",
        "Meal Plan Section": "Dinner",
        "Entry Type": "recipe",
        "Recipe": recipe,
        "Servings": servings,
        "Product": "",
        "Amount": "",
        "Quantity Unit": "",
        "Note": "",
    }
    row.update(overrides)
    return row


def product_entry(product="Banana", amount="2", unit="Each", **overrides):
    row = {
        "Day": "2026-11-01",
        "Meal Plan Section": "Breakfast",
        "Entry Type": "product",
        "Recipe": "",
        "Servings": "",
        "Product": product,
        "Amount": amount,
        "Quantity Unit": unit,
        "Note": "",
    }
    row.update(overrides)
    return row


def note_entry(note="Use leftovers", **overrides):
    row = {
        "Day": "2026-11-01",
        "Meal Plan Section": "Dinner",
        "Entry Type": "note",
        "Recipe": "",
        "Servings": "",
        "Product": "",
        "Amount": "",
        "Quantity Unit": "",
        "Note": note,
    }
    row.update(overrides)
    return row


class MealPlanSectionTests(TestCase):
    def test_builds_valid_section_payload(self):
        self.assertEqual(
            build_meal_plan_section_create_payload(section()),
            {"name": "Dinner", "sort_number": 30, "time_info": "18:00"},
        )

    def test_rejects_missing_name_and_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "cannot be blank"):
            build_meal_plan_section_create_payload(section(name=""))

        for field, value, message in (
            ("Sort Number", "-1", "zero or greater"),
            ("Sort Number", "1.5", "nonnegative integer"),
            ("Time", "25:00", "HH:MM"),
        ):
            with self.subTest(field=field, value=value):
                row = section()
                row[field] = value

                with self.assertRaisesRegex(ValueError, message):
                    build_meal_plan_section_create_payload(row)

    def test_existing_section_matches_and_update_is_safe(self):
        matching = build_resource_plan(
            MEAL_PLAN_SECTION_RESOURCE,
            [section()],
            [{"id": 3, "name": "Dinner", "sort_number": 30, "time_info": "18:00:00"}],
            LOOKUPS,
        )
        changed = build_resource_plan(
            MEAL_PLAN_SECTION_RESOURCE,
            [section(sort_number="40")],
            [{"id": 3, "name": "Dinner", "sort_number": 30, "time_info": "18:00"}],
            LOOKUPS,
        )

        self.assertEqual(len(matching["match"]), 1)
        self.assertEqual(
            MEAL_PLAN_SECTION_RESOURCE["build_update_payload"](
                changed["update"][0],
                LOOKUPS,
            ),
            {"sort_number": 40},
        )

    def test_duplicate_and_ambiguous_sections_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate name"):
            build_resource_plan(
                MEAL_PLAN_SECTION_RESOURCE,
                [section(), section(name=" dinner ")],
                [],
                LOOKUPS,
            )

        with self.assertRaisesRegex(ValueError, "duplicate names"):
            build_resource_plan(
                MEAL_PLAN_SECTION_RESOURCE,
                [],
                [
                    {"id": 3, "name": "Dinner"},
                    {"id": 4, "name": " dinner "},
                ],
                LOOKUPS,
            )

    def test_empty_catalog_preserves_unmanaged_sections(self):
        plan = build_resource_plan(
            MEAL_PLAN_SECTION_RESOURCE,
            [],
            [{"id": 3, "name": "Dinner"}],
            LOOKUPS,
        )

        self.assertEqual(plan, {"create": [], "update": [], "match": []})

    @patch("casita.apply.post")
    def test_controlled_section_creation_uses_registered_endpoint(self, post):
        plan = build_resource_plan(
            MEAL_PLAN_SECTION_RESOURCE,
            [section()],
            [],
            LOOKUPS,
        )

        result = apply_plan(MEAL_PLAN_SECTION_RESOURCE, plan)

        post.assert_called_once_with(
            "/objects/meal_plan_sections?query[]=id>0",
            {"name": "Dinner", "sort_number": 30, "time_info": "18:00"},
        )
        self.assertEqual(result["created"], 1)


class MealPlanPayloadTests(TestCase):
    def test_builds_recipe_product_and_note_payloads(self):
        self.assertEqual(
            build_meal_plan_create_payload(recipe_entry(), LOOKUPS),
            {
                "day": "2026-11-01",
                "type": "recipe",
                "section_id": 3,
                "recipe_id": 11,
                "recipe_servings": "2",
            },
        )
        self.assertEqual(
            build_meal_plan_create_payload(product_entry(), LOOKUPS),
            {
                "day": "2026-11-01",
                "type": "product",
                "section_id": 1,
                "product_id": 20,
                "product_amount": "2",
                "product_qu_id": 30,
            },
        )
        self.assertEqual(
            build_meal_plan_create_payload(note_entry(), LOOKUPS),
            {
                "day": "2026-11-01",
                "type": "note",
                "section_id": 3,
                "note": "Use leftovers",
            },
        )

    def test_rejects_missing_invalid_and_unsupported_values(self):
        invalid_rows = (
            (recipe_entry(Day=""), "YYYY-MM-DD"),
            (recipe_entry(**{"Entry Type": "event"}), "Entry Type"),
            (recipe_entry(**{"Meal Plan Section": "Unknown"}), "not found"),
            (recipe_entry(recipe="Unknown"), "not found"),
            (product_entry(product="Unknown"), "not found"),
            (product_entry(unit="Unknown"), "not found"),
            (product_entry(amount="0"), "greater than zero"),
            (note_entry(note=""), "cannot be blank"),
            (recipe_entry(Note="not native"), "not supported"),
        )

        for row, message in invalid_rows:
            with self.subTest(row=row):
                with self.assertRaisesRegex(ValueError, message):
                    build_meal_plan_create_payload(row, LOOKUPS)

    def test_update_payload_rejects_identity_and_runtime_fields(self):
        for field in ("day", "section_id", "recipe_id", "done"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "not safely managed"):
                    build_meal_plan_update_payload(
                        {
                            "name": "entry",
                            "changes": [
                                {"api_field": field, "catalog_value": 1}
                            ],
                        }
                    )


class MealPlanPlanningTests(TestCase):
    def test_cli_and_dependency_order(self):
        args = CLI.build_parser(
            ("all", "meal-plan-sections", "meal-plan")
        ).parse_args(["sync", "meal-plan", "--apply"])
        resources = list_sync_resources()

        self.assertEqual(args.sync_command, "meal-plan")
        self.assertTrue(args.apply)
        self.assertLess(
            resources.index("recipes"),
            resources.index("meal-plan-sections"),
        )
        self.assertLess(
            resources.index("meal-plan-sections"),
            resources.index("meal-plan"),
        )

    def test_multiple_entries_same_day_and_section_are_distinct(self):
        plan = build_resource_plan(
            MEAL_PLAN_RESOURCE,
            [recipe_entry(), recipe_entry(recipe="Pancakes")],
            [],
            LOOKUPS,
        )

        self.assertEqual(len(plan["create"]), 2)

    def test_duplicate_catalog_and_ambiguous_grocy_entries_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate identity"):
            build_resource_plan(
                MEAL_PLAN_RESOURCE,
                [recipe_entry(), recipe_entry(servings="4")],
                [],
                LOOKUPS,
            )

        native = {
            "id": 50,
            "day": "2026-11-01",
            "type": "recipe",
            "section_id": 3,
            "recipe_id": 11,
            "recipe_servings": "2",
            "done": 0,
        }

        with self.assertRaisesRegex(ValueError, "duplicate identity"):
            build_resource_plan(
                MEAL_PLAN_RESOURCE,
                [],
                [native, {**native, "id": 51}],
                LOOKUPS,
            )

    def test_existing_entries_match_idempotently_and_ignore_done(self):
        rows = [
            {
                "id": 50,
                "day": "2026-11-01",
                "type": "recipe",
                "section_id": 3,
                "recipe_id": 11,
                "recipe_servings": "2.0",
                "done": 1,
            },
            {
                "id": 51,
                "day": "2026-11-01",
                "type": "note",
                "section_id": 3,
                "note": "Use leftovers",
                "done": 1,
            },
        ]
        plan = build_resource_plan(
            MEAL_PLAN_RESOURCE,
            [recipe_entry(), note_entry()],
            rows,
            LOOKUPS,
        )

        self.assertEqual(len(plan["match"]), 2)
        self.assertEqual(plan["update"], [])

    def test_safe_amount_update_excludes_identity_and_runtime_state(self):
        plan = build_resource_plan(
            MEAL_PLAN_RESOURCE,
            [product_entry(amount="3")],
            [
                {
                    "id": 50,
                    "day": "2026-11-01",
                    "type": "product",
                    "section_id": 1,
                    "product_id": 20,
                    "product_amount": "2",
                    "product_qu_id": 30,
                    "done": 1,
                }
            ],
            LOOKUPS,
        )
        payload = build_meal_plan_update_payload(plan["update"][0])

        self.assertEqual(payload, {"product_amount": "3"})
        self.assertNotIn("day", payload)
        self.assertNotIn("section_id", payload)
        self.assertNotIn("done", payload)

    def test_date_or_section_change_never_updates_existing_entry(self):
        native = {
            "id": 50,
            "day": "2026-11-01",
            "type": "recipe",
            "section_id": 3,
            "recipe_id": 11,
            "recipe_servings": "2",
        }
        plan = build_resource_plan(
            MEAL_PLAN_RESOURCE,
            [recipe_entry(Day="2026-11-02")],
            [native],
            LOOKUPS,
        )

        self.assertEqual(len(plan["create"]), 1)
        self.assertEqual(plan["update"], [])

    def test_unmanaged_entries_are_preserved(self):
        plan = build_resource_plan(
            MEAL_PLAN_RESOURCE,
            [],
            [
                {
                    "id": 50,
                    "day": "2026-11-01",
                    "type": "note",
                    "section_id": 3,
                    "note": "Grocy-owned",
                }
            ],
            LOOKUPS,
        )

        self.assertEqual(plan, {"create": [], "update": [], "match": []})

    @patch("casita.sync_engine.get")
    def test_api_failures_are_propagated(self, get):
        get.side_effect = RuntimeError("Grocy unavailable")

        for resource, endpoint in (
            (
                MEAL_PLAN_SECTION_RESOURCE,
                "/objects/meal_plan_sections?query[]=id>0",
            ),
            (MEAL_PLAN_RESOURCE, "/objects/meal_plan"),
        ):
            with self.subTest(resource=resource["name"]):
                with self.assertRaisesRegex(RuntimeError, "Grocy unavailable"):
                    load_grocy(resource)

                get.assert_called_with(endpoint)

    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_dry_run_performs_no_writes(self, post, put):
        build_resource_plan(MEAL_PLAN_RESOURCE, [recipe_entry()], [], LOOKUPS)

        post.assert_not_called()
        put.assert_not_called()

    @patch("casita.apply.build_lookups", return_value=LOOKUPS)
    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_controlled_create_and_update_use_registered_endpoint(
        self,
        post,
        put,
        build_lookups,
    ):
        create_plan = build_resource_plan(
            MEAL_PLAN_RESOURCE,
            [recipe_entry()],
            [],
            LOOKUPS,
        )
        apply_plan(MEAL_PLAN_RESOURCE, create_plan)
        post.assert_called_once_with(
            "/objects/meal_plan",
            {
                "day": "2026-11-01",
                "type": "recipe",
                "section_id": 3,
                "recipe_id": 11,
                "recipe_servings": "2",
            },
        )

        update_plan = build_resource_plan(
            MEAL_PLAN_RESOURCE,
            [recipe_entry(servings="4")],
            [
                {
                    "id": 50,
                    "day": "2026-11-01",
                    "type": "recipe",
                    "section_id": 3,
                    "recipe_id": 11,
                    "recipe_servings": "2",
                    "done": 1,
                }
            ],
            LOOKUPS,
        )
        apply_plan(MEAL_PLAN_RESOURCE, update_plan)
        put.assert_called_once_with(
            "/objects/meal_plan/50",
            {"recipe_servings": "4"},
        )
        build_lookups.assert_called()
