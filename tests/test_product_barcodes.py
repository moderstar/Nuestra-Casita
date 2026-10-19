"""Tests for Grocy 4.6 product-barcode synchronization."""

import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from casita.apply import apply_plan
from casita.payloads import (
    build_product_barcode_create_payload,
    normalize_product_barcode,
)
from casita.registry import list_sync_resources
from casita.resources.product_barcodes import PRODUCT_BARCODE_RESOURCE
from casita.sync_engine import build_resource_plan, load_grocy


CLI_PATH = Path(__file__).resolve().parents[1] / "tools" / "casita.py"
CLI_SPEC = importlib.util.spec_from_file_location("casita_cli_barcodes", CLI_PATH)
CLI = importlib.util.module_from_spec(CLI_SPEC)
assert CLI_SPEC.loader is not None
CLI_SPEC.loader.exec_module(CLI)


LOOKUPS = {
    "products": {"Milk": 10, "Coffee": 11},
    "products_by_id": {10: "Milk", 11: "Coffee"},
}


def barcode(value="0012345678905", product="Milk"):
    return {"Barcode": value, "Product": product}


class ProductBarcodePayloadTests(TestCase):
    def test_builds_minimal_native_payload_and_preserves_leading_zeros(self):
        payload = build_product_barcode_create_payload(barcode(), LOOKUPS)

        self.assertEqual(
            payload,
            {"product_id": 10, "barcode": "0012345678905"},
        )

    def test_rejects_empty_barcode_values(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "non-empty"):
                    normalize_product_barcode(value)

    def test_rejects_missing_product_reference(self):
        with self.assertRaisesRegex(ValueError, "was not found in Grocy"):
            build_product_barcode_create_payload(
                barcode(product="Unknown"),
                LOOKUPS,
            )

    def test_does_not_impose_barcode_format_or_checksum_rules(self):
        payload = build_product_barcode_create_payload(
            barcode(value="internal-SKU:0007"),
            LOOKUPS,
        )

        self.assertEqual(payload["barcode"], "internal-SKU:0007")


class ProductBarcodePlanningTests(TestCase):
    def test_cli_parser_exposes_product_barcodes_command(self):
        args = CLI.build_parser(
            ("all", "products", "product-barcodes"),
        ).parse_args(["sync", "product-barcodes", "--apply"])

        self.assertEqual(args.command, "sync")
        self.assertEqual(args.sync_command, "product-barcodes")
        self.assertTrue(args.apply)

    def test_dependency_order_follows_products(self):
        resources = list_sync_resources()

        self.assertLess(
            resources.index("products"),
            resources.index("product-barcodes"),
        )

    def test_existing_association_is_an_idempotent_match(self):
        plan = build_resource_plan(
            PRODUCT_BARCODE_RESOURCE,
            [barcode()],
            [{"id": 20, "barcode": "0012345678905", "product_id": 10}],
            LOOKUPS,
        )

        self.assertEqual(len(plan["match"]), 1)
        self.assertEqual(plan["create"], [])
        self.assertEqual(plan["update"], [])

    def test_matching_is_case_insensitive_without_changing_payload_value(self):
        plan = build_resource_plan(
            PRODUCT_BARCODE_RESOURCE,
            [barcode(value="AbC-001")],
            [{"id": 20, "barcode": "abc-001", "product_id": 10}],
            LOOKUPS,
        )

        self.assertEqual(len(plan["match"]), 1)

    def test_multiple_barcodes_for_one_product_are_supported(self):
        plan = build_resource_plan(
            PRODUCT_BARCODE_RESOURCE,
            [barcode("0001"), barcode("0002")],
            [],
            LOOKUPS,
        )

        self.assertEqual(len(plan["create"]), 2)

    def test_duplicate_catalog_barcode_is_rejected_case_insensitively(self):
        with self.assertRaisesRegex(ValueError, "duplicate identity"):
            build_resource_plan(
                PRODUCT_BARCODE_RESOURCE,
                [barcode("ABC"), barcode("abc")],
                [],
                LOOKUPS,
            )

    def test_conflicting_product_assignment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "refusing to reassign"):
            build_resource_plan(
                PRODUCT_BARCODE_RESOURCE,
                [barcode(product="Coffee")],
                [
                    {
                        "id": 20,
                        "barcode": "0012345678905",
                        "product_id": 10,
                    }
                ],
                LOOKUPS,
            )

    def test_duplicate_native_barcode_is_rejected_conservatively(self):
        with self.assertRaisesRegex(ValueError, "duplicate identity"):
            build_resource_plan(
                PRODUCT_BARCODE_RESOURCE,
                [],
                [
                    {"id": 20, "barcode": "ABC", "product_id": 10},
                    {"id": 21, "barcode": "abc", "product_id": 11},
                ],
                LOOKUPS,
            )

    def test_unmanaged_grocy_barcodes_are_preserved(self):
        plan = build_resource_plan(
            PRODUCT_BARCODE_RESOURCE,
            [],
            [{"id": 20, "barcode": "unmanaged", "product_id": 10}],
            LOOKUPS,
        )

        self.assertEqual(plan, {"create": [], "update": [], "match": []})

    @patch("casita.sync_engine.get")
    def test_api_failure_is_propagated_without_mutation(self, get):
        get.side_effect = RuntimeError("Grocy unavailable")

        with self.assertRaisesRegex(RuntimeError, "Grocy unavailable"):
            load_grocy(PRODUCT_BARCODE_RESOURCE)

        get.assert_called_once_with("/objects/product_barcodes")

    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_dry_run_planning_performs_no_api_writes(self, post, put):
        plan = build_resource_plan(
            PRODUCT_BARCODE_RESOURCE,
            [barcode()],
            [],
            LOOKUPS,
        )

        self.assertEqual(len(plan["create"]), 1)
        post.assert_not_called()
        put.assert_not_called()

    @patch("casita.apply.build_lookups", return_value=LOOKUPS)
    @patch("casita.apply.post")
    def test_controlled_apply_creates_only_explicit_association(
        self,
        post,
        build_lookups,
    ):
        plan = build_resource_plan(
            PRODUCT_BARCODE_RESOURCE,
            [barcode()],
            [],
            LOOKUPS,
        )

        result = apply_plan(PRODUCT_BARCODE_RESOURCE, plan)

        post.assert_called_once_with(
            "/objects/product_barcodes",
            {"product_id": 10, "barcode": "0012345678905"},
        )
        build_lookups.assert_called_once_with()
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 0)
