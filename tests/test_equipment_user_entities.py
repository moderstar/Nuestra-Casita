"""Tests for Grocy 4.6 Equipment and User Entity synchronization."""

import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from casita.apply import apply_plan
from casita.payloads import (
    build_equipment_create_payload,
    build_equipment_update_payload,
    build_user_entity_create_payload,
    build_user_entity_update_payload,
)
from casita.registry import list_sync_resources
from casita.resources.equipment import EQUIPMENT_RESOURCE
from casita.resources.user_entities import USER_ENTITY_RESOURCE
from casita.resources.userfields import USERFIELD_RESOURCE
from casita.sync_engine import build_resource_plan, load_grocy


CLI_PATH = Path(__file__).resolve().parents[1] / "tools" / "casita.py"
CLI_SPEC = importlib.util.spec_from_file_location(
    "casita_cli_equipment_user_entities",
    CLI_PATH,
)
CLI = importlib.util.module_from_spec(CLI_SPEC)
assert CLI_SPEC.loader is not None
CLI_SPEC.loader.exec_module(CLI)


def equipment(name="Air purifier", description="Living room unit"):
    return {"Equipment": name, "Description": description}


def grocy_equipment(**overrides):
    row = {
        "id": 8,
        "name": "Air purifier",
        "description": "Living room unit",
        "instruction_manual_file_name": "purifier.pdf",
        "userfields": {"serial": "ABC123"},
        "row_created_timestamp": "2026-10-01 10:00:00",
    }
    row.update(overrides)
    return row


def user_entity(
    name="pets",
    caption="Pets",
    description="Household pets",
    show="1",
    icon="fa-solid fa-paw",
):
    return {
        "Name": name,
        "Caption": caption,
        "Description": description,
        "Show in Sidebar": show,
        "Icon CSS Class": icon,
    }


def grocy_user_entity(**overrides):
    row = {
        "id": 3,
        "name": "pets",
        "caption": "Pets",
        "description": "Household pets",
        "show_in_sidebar_menu": 1,
        "icon_css_class": "fa-solid fa-paw",
        "row_created_timestamp": "2026-10-01 10:00:00",
    }
    row.update(overrides)
    return row


class EquipmentTests(TestCase):
    def test_builds_definition_only_payload(self):
        payload = build_equipment_create_payload(equipment())

        self.assertEqual(
            payload,
            {"name": "Air purifier", "description": "Living room unit"},
        )
        self.assertNotIn("instruction_manual_file_name", payload)
        self.assertNotIn("userfields", payload)

    def test_rejects_missing_name(self):
        with self.assertRaisesRegex(ValueError, "cannot be blank"):
            build_equipment_create_payload(equipment(name=""))

    def test_duplicate_and_ambiguous_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate name"):
            build_resource_plan(
                EQUIPMENT_RESOURCE,
                [equipment(), equipment(name=" air PURIFIER ")],
                [],
                {},
            )

        with self.assertRaisesRegex(ValueError, "duplicate names"):
            build_resource_plan(
                EQUIPMENT_RESOURCE,
                [],
                [
                    grocy_equipment(),
                    grocy_equipment(id=9, name="AIR PURIFIER"),
                ],
                {},
            )

    def test_matches_idempotently_and_ignores_runtime_data(self):
        plan = build_resource_plan(
            EQUIPMENT_RESOURCE,
            [equipment()],
            [grocy_equipment()],
            {},
        )

        self.assertEqual(len(plan["match"]), 1)
        self.assertEqual(plan["create"], [])
        self.assertEqual(plan["update"], [])

    def test_safe_update_preserves_manual_and_userfields(self):
        plan = build_resource_plan(
            EQUIPMENT_RESOURCE,
            [equipment(description="Bedroom unit")],
            [grocy_equipment()],
            {},
        )
        payload = build_equipment_update_payload(plan["update"][0])

        self.assertEqual(payload, {"description": "Bedroom unit"})
        self.assertNotIn("instruction_manual_file_name", payload)
        self.assertNotIn("userfields", payload)

    def test_update_rejects_unmanaged_fields(self):
        with self.assertRaisesRegex(ValueError, "not safely managed"):
            build_equipment_update_payload({
                "name": "Air purifier",
                "changes": [{
                    "api_field": "instruction_manual_file_name",
                    "catalog_value": "replacement.pdf",
                }],
            })

    def test_empty_catalog_preserves_unmanaged_equipment(self):
        plan = build_resource_plan(
            EQUIPMENT_RESOURCE,
            [],
            [grocy_equipment()],
            {},
        )

        self.assertEqual(plan, {"create": [], "update": [], "match": []})

    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_dry_run_and_controlled_apply(self, post, put):
        plan = build_resource_plan(
            EQUIPMENT_RESOURCE,
            [equipment()],
            [],
            {},
        )

        post.assert_not_called()
        put.assert_not_called()
        apply_plan(EQUIPMENT_RESOURCE, plan)
        post.assert_called_once_with(
            "/objects/equipment",
            {"name": "Air purifier", "description": "Living room unit"},
        )

    @patch("casita.sync_engine.get")
    def test_api_failure_is_propagated(self, get):
        get.side_effect = RuntimeError("Grocy unavailable")

        with self.assertRaisesRegex(RuntimeError, "Grocy unavailable"):
            load_grocy(EQUIPMENT_RESOURCE)


class UserEntityTests(TestCase):
    def test_builds_native_definition_payload(self):
        self.assertEqual(
            build_user_entity_create_payload(user_entity()),
            {
                "name": "pets",
                "caption": "Pets",
                "description": "Household pets",
                "show_in_sidebar_menu": 1,
                "icon_css_class": "fa-solid fa-paw",
            },
        )

    def test_rejects_invalid_definition(self):
        for row, message in (
            (user_entity(name=""), "Name cannot be blank"),
            (user_entity(name="pet records"), "letters, numbers"),
            (user_entity(caption=""), "Caption cannot be blank"),
            (user_entity(show="perhaps"), "must be 1 or 0"),
        ):
            with self.subTest(row=row):
                with self.assertRaisesRegex(ValueError, message):
                    build_user_entity_create_payload(row)

    def test_duplicate_and_ambiguous_definitions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate name"):
            build_resource_plan(
                USER_ENTITY_RESOURCE,
                [user_entity(), user_entity(name=" PETS ")],
                [],
                {},
            )

        with self.assertRaisesRegex(ValueError, "duplicate names"):
            build_resource_plan(
                USER_ENTITY_RESOURCE,
                [],
                [grocy_user_entity(), grocy_user_entity(id=4, name="PETS")],
                {},
            )

    def test_existing_definition_matches_idempotently(self):
        plan = build_resource_plan(
            USER_ENTITY_RESOURCE,
            [user_entity()],
            [grocy_user_entity()],
            {},
        )

        self.assertEqual(len(plan["match"]), 1)

    def test_safe_metadata_update_excludes_identity_and_records(self):
        plan = build_resource_plan(
            USER_ENTITY_RESOURCE,
            [user_entity(caption="Our pets", show="0", icon="")],
            [grocy_user_entity()],
            {},
        )
        payload = build_user_entity_update_payload(plan["update"][0])

        self.assertEqual(
            payload,
            {
                "caption": "Our pets",
                "show_in_sidebar_menu": 0,
                "icon_css_class": "",
            },
        )
        self.assertNotIn("name", payload)
        self.assertNotIn("userobjects", payload)
        self.assertNotIn("userfields", payload)

    def test_identity_and_schema_changes_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "immutable"):
            build_user_entity_update_payload({
                "name": "pets",
                "changes": [{"api_field": "name", "catalog_value": "animals"}],
            })

        catalog_field = {
            "Entity": "userentity-pets",
            "Name": "weight",
            "Caption": "Weight",
            "Type": "number-decimal",
            "Configuration": "",
            "Sort Number": "",
            "Show as Column": "1",
            "Mandatory": "0",
            "Default Value": "",
        }
        grocy_field = {
            "id": 11,
            "entity": "userentity-pets",
            "name": "weight",
            "caption": "Weight",
            "type": "text-single-line",
            "config": "",
            "sort_number": None,
            "show_as_column_in_tables": 1,
            "input_required": 0,
            "default_value": "",
        }

        with self.assertRaisesRegex(ValueError, "destructive schema migration"):
            build_resource_plan(
                USERFIELD_RESOURCE,
                [catalog_field],
                [grocy_field],
                {},
            )

    def test_empty_catalog_preserves_definitions_records_and_fields(self):
        plan = build_resource_plan(
            USER_ENTITY_RESOURCE,
            [],
            [grocy_user_entity()],
            {},
        )

        self.assertEqual(plan, {"create": [], "update": [], "match": []})

    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_dry_run_and_controlled_apply(self, post, put):
        plan = build_resource_plan(
            USER_ENTITY_RESOURCE,
            [user_entity()],
            [],
            {},
        )

        post.assert_not_called()
        put.assert_not_called()
        apply_plan(USER_ENTITY_RESOURCE, plan)
        post.assert_called_once_with(
            "/objects/userentities",
            build_user_entity_create_payload(user_entity()),
        )

    @patch("casita.sync_engine.get")
    def test_api_failure_is_propagated(self, get):
        get.side_effect = RuntimeError("Grocy unavailable")

        with self.assertRaisesRegex(RuntimeError, "Grocy unavailable"):
            load_grocy(USER_ENTITY_RESOURCE)


class IntegrationTests(TestCase):
    def test_cli_exposes_both_resources(self):
        parser = CLI.build_parser(("all", "equipment", "user-entities"))

        equipment_args = parser.parse_args(["sync", "equipment", "--apply"])
        user_entity_args = parser.parse_args(
            ["sync", "user-entities", "--apply"]
        )

        self.assertTrue(equipment_args.apply)
        self.assertTrue(user_entity_args.apply)

    def test_dependency_order_places_definitions_before_userfields(self):
        resources = list_sync_resources()

        self.assertLess(
            resources.index("user-entities"),
            resources.index("userfields"),
        )
        self.assertIn("equipment", resources)
