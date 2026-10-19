"""Tests for the Grocy 4.6 shopping-list read capability."""

from decimal import Decimal
from unittest import TestCase

from casita.application import IntegrationDirectory, ShoppingService
from casita.integrations import Capability, ReadRequest
from casita.integrations.grocy import GrocyReadAdapter


class FakeGrocyReader:
    def __init__(self, responses=None, error=None):
        self.responses = responses or {}
        self.error = error
        self.endpoints = []

    def get(self, endpoint):
        self.endpoints.append(endpoint)

        if self.error is not None:
            raise self.error

        return self.responses[endpoint]


def shopping_responses(*, lists, items, products=(), units=()):
    return {
        "/objects/shopping_lists": list(lists),
        "/objects/shopping_list": list(items),
        "/objects/products": list(products),
        "/objects/quantity_units": list(units),
    }


class GrocyShoppingListTests(TestCase):
    def read(self, responses):
        reader = FakeGrocyReader(responses)
        adapter = GrocyReadAdapter(reader, timezone_name="America/Los_Angeles")
        snapshot = adapter.read(
            ReadRequest(
                household_id="household",
                capabilities=frozenset({Capability.SHOPPING}),
            )
        )
        return snapshot.data[0].records, reader.endpoints

    def test_reads_multiple_lists_and_resolves_products_and_units(self):
        records, endpoints = self.read(
            shopping_responses(
                lists=(
                    {"id": 2, "name": "Hardware"},
                    {"id": 1, "name": "Groceries"},
                ),
                items=(
                    {
                        "id": 10,
                        "shopping_list_id": 1,
                        "product_id": 20,
                        "amount": "2.50",
                        "qu_id": 30,
                        "done": 0,
                        "note": "Organic",
                    },
                    {
                        "id": 11,
                        "shopping_list_id": 2,
                        "product_id": None,
                        "amount": "0",
                        "qu_id": None,
                        "done": 1,
                        "note": "Picture hooks",
                    },
                ),
                products=({"id": 20, "name": "Milk"},),
                units=({"id": 30, "name": "bottles"},),
            )
        )

        self.assertEqual([record.name for record in records], ["Groceries", "Hardware"])
        groceries, hardware = records
        self.assertEqual(groceries.items[0].name, "Milk")
        self.assertEqual(groceries.items[0].quantity, Decimal("2.50"))
        self.assertEqual(groceries.items[0].unit, "bottles")
        self.assertFalse(groceries.items[0].checked)
        self.assertEqual(groceries.items[0].note, "Organic")
        self.assertEqual(hardware.items[0].name, "Picture hooks")
        self.assertEqual(hardware.items[0].quantity, Decimal("0"))
        self.assertTrue(hardware.items[0].checked)
        self.assertEqual(
            endpoints,
            [
                "/objects/shopping_lists",
                "/objects/shopping_list",
                "/objects/products",
                "/objects/quantity_units",
            ],
        )

    def test_preserves_empty_lists(self):
        records, _ = self.read(
            shopping_responses(
                lists=({"id": 1, "name": "Groceries"},),
                items=(),
            )
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].items, ())

    def test_rejects_missing_product_reference(self):
        with self.assertRaisesRegex(ValueError, "unknown product '99'"):
            self.read(
                shopping_responses(
                    lists=({"id": 1, "name": "Groceries"},),
                    items=(
                        {
                            "id": 10,
                            "shopping_list_id": 1,
                            "product_id": 99,
                        },
                    ),
                )
            )

    def test_rejects_missing_quantity_unit_reference(self):
        with self.assertRaisesRegex(ValueError, "unknown quantity unit '99'"):
            self.read(
                shopping_responses(
                    lists=({"id": 1, "name": "Groceries"},),
                    items=(
                        {
                            "id": 10,
                            "shopping_list_id": 1,
                            "product_id": 20,
                            "qu_id": 99,
                        },
                    ),
                    products=({"id": 20, "name": "Milk"},),
                )
            )

    def test_rejects_missing_list_reference(self):
        with self.assertRaisesRegex(ValueError, "unknown shopping list '2'"):
            self.read(
                shopping_responses(
                    lists=({"id": 1, "name": "Groceries"},),
                    items=({"id": 10, "shopping_list_id": 2},),
                )
            )

    def test_api_failure_is_returned_as_structured_service_failure(self):
        reader = FakeGrocyReader(error=RuntimeError("Grocy unavailable"))
        adapter = GrocyReadAdapter(reader)
        service = ShoppingService(
            IntegrationDirectory(
                (adapter,),
                owners={Capability.SHOPPING: ("grocy",)},
            )
        )

        result = service.read("household")

        self.assertEqual(result.records, ())
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].integration_key, "grocy")
        self.assertEqual(result.failures[0].message, "Grocy unavailable")

    def test_shopping_capability_has_no_write_or_sync_side_effects(self):
        reader = FakeGrocyReader(
            shopping_responses(
                lists=({"id": 1, "name": "Groceries"},),
                items=(),
            )
        )
        adapter = GrocyReadAdapter(reader)

        adapter.read(
            ReadRequest(
                household_id="household",
                capabilities=frozenset({Capability.SHOPPING}),
            )
        )

        self.assertTrue(all(endpoint.startswith("/objects/") for endpoint in reader.endpoints))
