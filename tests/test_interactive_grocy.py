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
    ChoreDefinition,
    ChoreUserOption,
    CompleteChore,
    DeactivateChore,
    IntegrationDescriptor,
    IntegrationSnapshot,
    ReadRequest,
    RemoveShoppingItem,
    ShoppingItemStateChange,
    UpdateChoreDefinition,
)
from casita.integrations.grocy import GrocyReadAdapter
from casita.integrations.grocy.mapping import domain_id
from casita.registry import get_resource, list_sync_commands, list_sync_resources


class RecordingGrocy:
    def __init__(self):
        self.responses = {
            "/objects/shopping_lists": [{"id": 1, "name": "Groceries"}],
            "/objects/shopping_list": [{"id": 10, "shopping_list_id": 1, "product_id": 2, "amount": "1", "qu_id": 3, "done": 0}],
            "/objects/products": [{"id": 2, "name": "Milk", "qu_id_purchase": 3, "active": 1}],
            "/objects/quantity_units": [{"id": 3, "name": "carton"}],
            "/objects/chores": [{"id": 4, "name": "Sweep", "start_date": "2026-10-20 08:00:00", "active": 1, "period_type": "weekly", "period_interval": 1, "period_days": 1, "period_config": "monday", "assignment_type": "random", "assignment_config": "7"}],
            "/objects/chores_log": [],
            "/users": [{"id": 7, "username": "miguel", "display_name": "Miguel"}],
            "/chores": [{"chore_id": 4, "next_estimated_execution_time": "2026-10-27 08:00:00", "next_execution_assigned_to_user_id": 7}],
        }
        self.calls = []

    def get(self, endpoint):
        return self.responses[endpoint]

    def post(self, endpoint, payload):
        self.calls.append(("POST", endpoint, payload))
        if endpoint == "/objects/chores":
            return {"created_object_id": 5}

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

    def test_read_projects_schedule_assignments_and_inactive_definitions(self):
        self.client.responses["/objects/chores"].append({
            "id": 6, "name": "Seasonal", "start_date": "2026-10-20 09:00:00",
            "active": 0, "period_type": "manually", "period_interval": 1,
            "period_days": 1, "period_config": "", "assignment_type": "no-assignment",
            "assignment_config": "",
        })
        self.client.responses["/objects/chores_log"] = [{"id": 1, "chore_id": 4}]
        snapshot = self.adapter.read(ReadRequest("home", frozenset({Capability.CHORES})))
        by_name = {item.name: item for item in snapshot.data[0].records}
        self.assertEqual(set(by_name), {"Sweep", "Seasonal"})
        self.assertEqual(by_name["Sweep"].schedule_weekdays, ("monday",))
        self.assertEqual(by_name["Sweep"].assigned_person_name, "Miguel")
        self.assertFalse(by_name["Sweep"].start_at_editable)
        self.assertFalse(by_name["Seasonal"].active)

    def chore_definition(self):
        return ChoreDefinition(
            "home", "Mop", "Kitchen", "weekly", 1, 1,
            ("monday", "friday"), datetime(2026, 10, 21, 15, tzinfo=timezone.utc),
            "in-alphabetical-order", (domain_id("person", 7),), True,
        )

    def test_create_chore_maps_schedule_assignment_and_recalculates(self):
        self.adapter.create_chore(self.chore_definition())
        create = self.client.calls[-2]
        self.assertEqual(create[0:2], ("POST", "/objects/chores"))
        self.assertEqual(create[2]["period_type"], "weekly")
        self.assertEqual(create[2]["period_config"], "monday,friday")
        self.assertEqual(create[2]["assignment_config"], "7")
        self.assertEqual(
            self.client.calls[-1],
            ("POST", "/chores/executions/calculate-next-assignments", {"chore_id": 5}),
        )

    def test_edit_rejects_start_date_change_after_execution(self):
        self.client.responses["/objects/chores_log"] = [{"id": 1, "chore_id": 4}]
        definition = self.chore_definition()
        command = UpdateChoreDefinition(
            definition.household_id, domain_id("chore", 4), definition.name,
            definition.description, definition.schedule_type,
            definition.schedule_interval, definition.schedule_day,
            definition.schedule_weekdays, definition.start_at,
            definition.assignment_type, definition.assignment_user_ids,
            definition.active,
        )
        with self.assertRaisesRegex(ValueError, "cannot change"):
            self.adapter.update_chore(command)
        self.assertFalse(any(call[0] == "PUT" for call in self.client.calls))

    def test_edit_preserves_an_unchanged_start_date_after_execution(self):
        self.client.responses["/objects/chores_log"] = [{"id": 1, "chore_id": 4}]
        definition = self.chore_definition()
        command = UpdateChoreDefinition(
            definition.household_id, domain_id("chore", 4), definition.name,
            definition.description, definition.schedule_type,
            definition.schedule_interval, definition.schedule_day,
            definition.schedule_weekdays,
            datetime(2026, 10, 20, 8, tzinfo=timezone.utc),
            definition.assignment_type, definition.assignment_user_ids,
            definition.active,
        )
        self.adapter.update_chore(command)
        update = next(call for call in self.client.calls if call[0] == "PUT")
        self.assertNotIn("start_date", update[2])

    def test_deactivation_never_deletes_history(self):
        self.adapter.deactivate_chore(DeactivateChore("home", domain_id("chore", 4)))
        self.assertEqual(self.client.calls[-1], ("PUT", "/objects/chores/4", {"active": 0}))
        self.assertFalse(any(call[0] == "DELETE" for call in self.client.calls))


class ChoreSynchronizationRetirementTests(TestCase):
    def test_chores_cannot_be_planned_or_applied_by_legacy_sync(self):
        self.assertNotIn("chores", list_sync_resources())
        self.assertNotIn("chores", list_sync_commands())
        with self.assertRaisesRegex(ValueError, "Unknown resource"):
            get_resource("chores")

    def test_unrelated_resources_remain_registered(self):
        resources = list_sync_resources()
        self.assertIn("products", resources)
        self.assertIn("tasks", resources)
        self.assertIn("meal-plan", resources)


class InteractiveIntegration:
    descriptor = IntegrationDescriptor(
        key="interactive", display_name="Interactive",
        capabilities=frozenset({Capability.SHOPPING, Capability.CHORES}),
    )

    def __init__(self):
        self.items = ()
        self.add_calls = 0
        self.completed = False
        self.chore = Chore(
            "chore", "home", "Sweep", start_at=datetime(2026, 10, 20, tzinfo=timezone.utc)
        )
        self.chore_create_calls = 0
        self.chore_error = None

    def health(self):
        raise NotImplementedError

    def read(self, request: ReadRequest):
        now = datetime.now(timezone.utc)
        capability = next(iter(request.capabilities))
        records = (
            (ShoppingList("list", request.household_id, "Groceries", self.items),)
            if capability == Capability.SHOPPING
            else (replace(self.chore, household_id=request.household_id, completed=self.completed),)
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

    def list_chore_users(self):
        return (ChoreUserOption("person", "Miguel"),)

    def create_chore(self, command):
        if self.chore_error is not None:
            raise self.chore_error
        self.chore_create_calls += 1
        self.chore = replace(
            self.chore, name=command.name, description=command.description,
            schedule_type=command.schedule_type, schedule_interval=command.schedule_interval,
            schedule_day=command.schedule_day, schedule_weekdays=command.schedule_weekdays,
            start_at=command.start_at, assignment_type=command.assignment_type,
            assignment_user_ids=command.assignment_user_ids, active=command.active,
        )

    def update_chore(self, command):
        self.chore = replace(
            self.chore, name=command.name, description=command.description,
            schedule_type=command.schedule_type, schedule_interval=command.schedule_interval,
            schedule_day=command.schedule_day, schedule_weekdays=command.schedule_weekdays,
            start_at=command.start_at, assignment_type=command.assignment_type,
            assignment_user_ids=command.assignment_user_ids, active=command.active,
        )

    def deactivate_chore(self, command):
        self.chore = replace(self.chore, active=False)


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

    def chore_payload(self):
        return {
            "name": "Mop", "description": "Kitchen", "schedule_type": "weekly",
            "schedule_interval": 1, "schedule_day": 1,
            "schedule_weekdays": ["monday", "friday"],
            "start_at": "2026-10-21T15:00:00+00:00",
            "assignment_type": "in-alphabetical-order",
            "assignment_user_ids": ["person"], "active": True,
        }

    def test_create_chore_is_csrf_protected_and_idempotent(self):
        denied = self.client.post(
            "/api/v1/chores", json=self.chore_payload(),
            headers={"Idempotency-Key": "chore-create-1"},
        )
        self.assertEqual(denied.status_code, 403)
        first = self.client.post(
            "/api/v1/chores", json=self.chore_payload(),
            headers=self.headers("chore-create-1"),
        )
        second = self.client.post(
            "/api/v1/chores", json=self.chore_payload(),
            headers=self.headers("chore-create-1"),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(self.integration.chore_create_calls, 1)

    def test_recurrence_and_assignment_validation(self):
        payload = self.chore_payload()
        payload["schedule_weekdays"] = []
        response = self.client.post(
            "/api/v1/chores", json=payload, headers=self.headers("invalid-weekly"),
        )
        self.assertEqual(response.status_code, 400)
        payload = self.chore_payload()
        payload["assignment_user_ids"] = []
        response = self.client.post(
            "/api/v1/chores", json=payload, headers=self.headers("invalid-assignment"),
        )
        self.assertEqual(response.status_code, 400)

    def test_edit_and_deactivate_return_refreshed_state(self):
        payload = self.chore_payload()
        payload["name"] = "Mop downstairs"
        updated = self.client.put(
            "/api/v1/chores/chore", json=payload, headers=self.headers("chore-edit-1"),
        )
        self.assertEqual(updated.json()["data"][0]["name"], "Mop downstairs")
        deactivated = self.client.post(
            "/api/v1/chores/chore/deactivate", headers=self.headers("chore-off-1"),
        )
        self.assertFalse(deactivated.json()["data"][0]["active"])

    def test_chore_users_are_opaque_and_authenticated(self):
        anonymous = TestClient(self.client.app)
        self.assertEqual(anonymous.get("/api/v1/chore-users").status_code, 401)
        response = self.client.get("/api/v1/chore-users")
        self.assertEqual(response.json()["data"], [{"id": "person", "display_name": "Miguel"}])

    def test_grocy_failure_is_safe_and_does_not_consume_idempotency_key(self):
        self.integration.chore_error = RuntimeError("secret Grocy response")
        failed = self.client.post(
            "/api/v1/chores", json=self.chore_payload(),
            headers=self.headers("retry-create-1"),
        )
        self.assertEqual(failed.status_code, 502)
        self.assertNotIn("secret Grocy response", failed.text)
        self.integration.chore_error = None
        retried = self.client.post(
            "/api/v1/chores", json=self.chore_payload(),
            headers=self.headers("retry-create-1"),
        )
        self.assertEqual(retried.status_code, 200)
