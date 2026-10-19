"""Tests for Grocy 4.6 quantity-unit conversion synchronization."""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from casita.payloads import (
    build_quantity_unit_conversion_create_payload,
    build_quantity_unit_conversion_update_payload,
    parse_conversion_factor,
)
from casita.apply import apply_plan
from casita.registry import list_sync_resources
from casita.resources.quantity_unit_conversions import (
    QUANTITY_UNIT_CONVERSION_RESOURCE,
)
from casita.sync_engine import build_resource_plan, load_grocy


LOOKUPS = {
    "units": {"Each": 1, "Package": 2, "Gram": 3},
    "units_by_id": {1: "Each", 2: "Package", 3: "Gram"},
    "products": {"Eggs": 10, "Flour": 11},
    "products_by_id": {10: "Eggs", 11: "Flour"},
}


def conversion(
    source="Package",
    target="Each",
    factor="6",
    product="",
):
    return {
        "From Quantity Unit": source,
        "To Quantity Unit": target,
        "Factor": factor,
        "Product": product,
    }


class QuantityUnitConversionPayloadTests(TestCase):
    def test_builds_global_conversion(self):
        payload = build_quantity_unit_conversion_create_payload(
            conversion(factor="0.0012500"),
            LOOKUPS,
        )

        self.assertEqual(
            payload,
            {
                "from_qu_id": 2,
                "to_qu_id": 1,
                "factor": "0.0012500",
                "product_id": None,
            },
        )

    def test_builds_product_specific_conversion(self):
        payload = build_quantity_unit_conversion_create_payload(
            conversion(product="Eggs"),
            LOOKUPS,
        )

        self.assertEqual(payload["product_id"], 10)
        self.assertEqual(payload["factor"], "6")

    def test_factor_uses_decimal_precision(self):
        factor = parse_conversion_factor("0.123456789012345678901")

        self.assertIsInstance(factor, Decimal)
        self.assertEqual(factor, Decimal("0.123456789012345678901"))

    def test_rejects_invalid_zero_negative_and_nonfinite_factors(self):
        for value in ("", "invalid", "0", "-1", "NaN", "Infinity"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Factor"):
                    parse_conversion_factor(value)

    def test_rejects_missing_quantity_unit(self):
        with self.assertRaisesRegex(ValueError, "was not found in Grocy"):
            build_quantity_unit_conversion_create_payload(
                conversion(source="Case"),
                LOOKUPS,
            )

    def test_rejects_missing_product(self):
        with self.assertRaisesRegex(ValueError, "was not found in Grocy"):
            build_quantity_unit_conversion_create_payload(
                conversion(product="Milk"),
                LOOKUPS,
            )

    def test_rejects_same_source_and_target(self):
        with self.assertRaisesRegex(ValueError, "must differ"):
            build_quantity_unit_conversion_create_payload(
                conversion(source="Each", target="Each"),
                LOOKUPS,
            )

    def test_update_revalidates_factor(self):
        payload = build_quantity_unit_conversion_update_payload(
            {
                "name": "Global: Package -> Each",
                "changes": [
                    {
                        "api_field": "factor",
                        "catalog_value": Decimal("6.000"),
                    }
                ],
            }
        )

        self.assertEqual(payload, {"factor": "6.000"})


class QuantityUnitConversionPlanningTests(TestCase):
    def test_dependency_order_follows_quantity_units_and_products(self):
        resources = list_sync_resources()

        self.assertLess(
            resources.index("quantity-units"),
            resources.index("quantity-unit-conversions"),
        )
        self.assertLess(
            resources.index("products"),
            resources.index("quantity-unit-conversions"),
        )

    def test_idempotent_conversion_is_a_match(self):
        plan = build_resource_plan(
            QUANTITY_UNIT_CONVERSION_RESOURCE,
            [conversion(factor="6.000")],
            [
                {
                    "id": 100,
                    "from_qu_id": 2,
                    "to_qu_id": 1,
                    "factor": "6",
                    "product_id": None,
                }
            ],
            LOOKUPS,
        )

        self.assertEqual(len(plan["match"]), 1)
        self.assertEqual(plan["create"], [])
        self.assertEqual(plan["update"], [])

    def test_factor_change_produces_update(self):
        plan = build_resource_plan(
            QUANTITY_UNIT_CONVERSION_RESOURCE,
            [conversion(factor="12")],
            [
                {
                    "id": 100,
                    "from_qu_id": 2,
                    "to_qu_id": 1,
                    "factor": "6",
                    "product_id": None,
                }
            ],
            LOOKUPS,
        )

        self.assertEqual(len(plan["update"]), 1)
        self.assertEqual(
            plan["update"][0]["changes"][0]["catalog_value"],
            Decimal("12"),
        )

    def test_global_and_product_specific_conversions_are_distinct(self):
        plan = build_resource_plan(
            QUANTITY_UNIT_CONVERSION_RESOURCE,
            [conversion(), conversion(product="Eggs")],
            [],
            LOOKUPS,
        )

        self.assertEqual(len(plan["create"]), 2)

    def test_duplicate_and_conflicting_catalog_definitions_are_rejected(self):
        for second_factor in ("6", "12"):
            with self.subTest(second_factor=second_factor):
                with self.assertRaisesRegex(
                    ValueError,
                    "duplicate identity",
                ):
                    build_resource_plan(
                        QUANTITY_UNIT_CONVERSION_RESOURCE,
                        [conversion(), conversion(factor=second_factor)],
                        [],
                        LOOKUPS,
                    )

    def test_duplicate_grocy_definition_is_rejected(self):
        grocy_row = {
            "id": 100,
            "from_qu_id": 2,
            "to_qu_id": 1,
            "factor": "6",
            "product_id": None,
        }

        with self.assertRaisesRegex(ValueError, "duplicate identity"):
            build_resource_plan(
                QUANTITY_UNIT_CONVERSION_RESOURCE,
                [],
                [grocy_row, {**grocy_row, "id": 101}],
                LOOKUPS,
            )

    def test_unmanaged_grocy_conversion_is_preserved(self):
        plan = build_resource_plan(
            QUANTITY_UNIT_CONVERSION_RESOURCE,
            [],
            [
                {
                    "id": 100,
                    "from_qu_id": 2,
                    "to_qu_id": 1,
                    "factor": "6",
                    "product_id": None,
                }
            ],
            LOOKUPS,
        )

        self.assertEqual(plan, {"create": [], "update": [], "match": []})

    @patch("casita.sync_engine.get")
    def test_api_failure_is_propagated_without_mutation(self, get):
        get.side_effect = RuntimeError("Grocy unavailable")

        with self.assertRaisesRegex(RuntimeError, "Grocy unavailable"):
            load_grocy(QUANTITY_UNIT_CONVERSION_RESOURCE)

        get.assert_called_once_with("/objects/quantity_unit_conversions")

    @patch("casita.apply.put")
    @patch("casita.apply.post")
    def test_dry_run_planning_performs_no_api_writes(self, post, put):
        plan = build_resource_plan(
            QUANTITY_UNIT_CONVERSION_RESOURCE,
            [conversion()],
            [],
            LOOKUPS,
        )

        self.assertEqual(len(plan["create"]), 1)
        post.assert_not_called()
        put.assert_not_called()

    @patch("casita.apply.build_lookups", return_value=LOOKUPS)
    @patch("casita.apply.post")
    def test_controlled_apply_uses_registered_endpoint(
        self,
        post,
        build_lookups,
    ):
        plan = build_resource_plan(
            QUANTITY_UNIT_CONVERSION_RESOURCE,
            [conversion(product="Eggs")],
            [],
            LOOKUPS,
        )

        result = apply_plan(QUANTITY_UNIT_CONVERSION_RESOURCE, plan)

        post.assert_called_once_with(
            "/objects/quantity_unit_conversions",
            {
                "from_qu_id": 2,
                "to_qu_id": 1,
                "factor": "6",
                "product_id": 10,
            },
        )
        build_lookups.assert_called_once_with()
        self.assertEqual(result["created"], 1)
