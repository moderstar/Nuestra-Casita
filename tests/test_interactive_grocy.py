"""Tests for bounded interactive Grocy shopping and chore operations."""

import os
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase

from fastapi.testclient import TestClient

from casita.api import DashboardApiConfiguration, create_dashboard_api
from casita.bootstrap import ApplicationConfiguration, build_application
from casita.domain import Chore, ShoppingItem, ShoppingList
from casita.integrations import (
    AddShoppingItem,
    Capability,
    CapabilityData,
    CompleteChore,
    IntegrationDescriptor,
    IntegrationSnapshot,
    ReadRequest,
    RemoveShoppingItem,
    ShoppingItemStateChange,
)
from casita.integrations.grocy import GrocyReadAdapter
from casita.integrations.grocy.mapping import domain_id


class RecordingGrocy:
    def __init__(self):
        self.responses = {
            "/objects/shopping_lists": [{"id": 1, "name": "Groceries"}],
            "/objects/shopping_list": [{"id": 10, "shopping_list_id": 1, "product_id": 2, "amount": "1", "qu_id": 3, "done": 0}],
            "/objects/products": [{"id": 2, "name": "Milk", "qu_id_purchase": 3, "active": 1}],
            "/objects/quantity_units": [{"id": 3, "name": "carton"}],
            "/objects/chores": [{"id": 4, "name": "Sweep"}],
        }
        self.calls = []

    def get(self, endpoint):
        return self.responses[endpoint]

    def post(self, endpoint, payload):
        self.calls.append(("POST", endpoint, payload))

    def put(self, endpoint, payload):
        self.calls.append(("PUT", endpoint, payload))

    def delete(self, endpoint):
        self.calls.append(("DELETE", endpoint, None))


class GrocyMutationAdapterTests(TestCase):
    def setUp(self):
        self.client = RecordingGrocy()
        self.adapter = GrocyReadAdapter(self.client)
        self.list_id = domain_id("shopping-list", 1)
        self.item_id = domain_id("shopping-item", 10)
        self.product_id = domain_id("product", 2)
        self.unit_id = domain_id("quantity-unit", 3)

    def test_product_search_is_bounded_and_opaque(self):
        result = self.adapter.search_shopping_products("mil", limit=5)
        self.assertEqual(result[0].id, self.product_id)
        self.assertEqual(result[0].unit, "carton")
        self.assertNotEqual(result[0].id, "2")

    def test_add_product_preserves_decimal_and_uses_generic_object_api(self):
        self.adapter.add_shopping_item(AddShoppingItem(
            "home", self.list_id, Decimal("1.250"), self.product_id, self.unit_id, "cold",
        ))
        method, endpoint, payload = self.client.calls[-1]
        self.assertEqual((method, endpoint), ("POST", "/objects/shopping_list"))
        self.assertEqual(payload["amount"], "1.250")
        self.assertEqual(payload["product_id"], 2)
        self.assertEqual(payload["done"], 0)

    def test_mark_done_is_list_only_and_idempotent(self):
        command = ShoppingItemStateChange("home", self.list_id, self.item_id, True)
        self.adapter.set_shopping_item_purchased(command)
        self.assertEqual(self.client.calls, [("PUT", "/objects/shopping_list/10", {"done": 1})])
        self.client.responses["/objects/shopping_list"][0]["done"] = 1
        self.adapter.set_shopping_item_purchased(command)
        self.assertEqual(len(self.client.calls), 1)

    def test_remove_verifies_list_membership(self):
        self.adapter.remove_shopping_item(RemoveShoppingItem("home", self.list_id, self.item_id))
        self.assertEqual(self.client.calls[-1], ("DELETE", "/objects/shopping_list/10", None))

    def test_complete_chore_uses_execution_operation(self):
        self.adapter.complete_chore(CompleteChore("home", domain_id("chore", 4)))
        self.assertEqual(self.client.calls[-1], ("POST", "/chores/4/execute", {"tracked_time": "", "done_by": ""}))


class InteractiveIntegration:
    descriptor = IntegrationDescriptor(
        key="interactive", display_name="Interactive",
        capabilities=frozenset({Capability.SHOPPING, Capability.CHORES}),
    )

    def __init__(self):
        self.items = ()
        self.add_calls = 0
        self.completed = False

    def health(self):
        raise NotImplementedError

    def read(self, request: ReadRequest):
        now = datetime.now(timezone.utc)
        capability = next(iter(request.capabilities))
        records = (
            (ShoppingList("list", request.household_id, "Groceries", self.items),)
            if capability == Capability.SHOPPING
            else (Chore("chore", request.household_id, "Sweep", completed=self.completed),)
        )
        return IntegrationSnapshot("interactive", request.household_id, now, (CapabilityData(capability, records, now),))

    def search_shopping_products(self, query, *, limit):
        return ()

    def add_shopping_item(self, command):
        self.add_calls += 1
        self.items = (ShoppingItem("item", command.note or "Milk", command.quantity),)

    def set_shopping_item_purchased(self, command):
        item = self.items[0]
        self.items = (replace(item, checked=command.purchased),)

    def remove_shopping_item(self, command):
        self.items = ()

    def complete_chore(self, command):
        self.completed = True


class InteractiveApiTests(TestCase):
    def setUp(self):
        self.integration = InteractiveIntegration()
        app = build_application(
            integrations=(self.integration,),
            capability_owners={
                Capability.SHOPPING: ("interactive",),
                Capability.CHORES: ("interactive",),
            },
        )
        app = replace(app, configuration=ApplicationConfiguration(
            project_root=os.path.abspath("."), source=None,
            grocy_url="http://grocy", grocy_api_key="hidden",
            timezone="UTC", household_id="home", household_name="Our Home",
        ))
        self.client = TestClient(create_dashboard_api(app, DashboardApiConfiguration(
            password="correct horse battery", session_secret="s" * 32, cookie_secure=False,
        )))
        self.client.post("/api/v1/session", json={"password": "correct horse battery"})

    def headers(self, key="operation-0001"):
        return {"X-CSRF-Token": self.client.cookies["casita_csrf"], "Idempotency-Key": key}

    def test_csrf_is_required_for_mutation(self):
        response = self.client.post("/api/v1/chores/chore/complete", headers={"Idempotency-Key": "operation-0001"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.integration.completed)

    def test_duplicate_add_is_applied_once_and_returns_refreshed_data(self):
        payload = {"product_id": None, "unit_id": None, "quantity": "1.50", "note": "Bananas"}
        first = self.client.post("/api/v1/shopping-lists/list/items", json=payload, headers=self.headers())
        second = self.client.post("/api/v1/shopping-lists/list/items", json=payload, headers=self.headers())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(self.integration.add_calls, 1)
        self.assertEqual(first.json()["data"][0]["items"][0]["quantity"], "1.50")

    def test_same_key_with_different_payload_is_conflict(self):
        self.client.post("/api/v1/shopping-lists/list/items", json={"quantity": 1, "note": "A"}, headers=self.headers())
        response = self.client.post("/api/v1/shopping-lists/list/items", json={"quantity": 1, "note": "B"}, headers=self.headers())
        self.assertEqual(response.status_code, 409)

    def test_validation_rejects_zero_without_write(self):
        response = self.client.post("/api/v1/shopping-lists/list/items", json={"quantity": 0, "note": "A"}, headers=self.headers())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.integration.add_calls, 0)

    def test_chore_completion_returns_authoritative_state(self):
        response = self.client.post("/api/v1/chores/chore/complete", headers=self.headers())
        self.assertTrue(response.json()["data"][0]["completed"])
