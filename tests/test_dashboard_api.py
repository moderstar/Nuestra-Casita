"""Tests for dashboard read projections and authenticated HTTP transport."""

import os
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from casita.api import (
    DashboardApiConfiguration,
    create_dashboard_api,
    json_value,
    load_dashboard_api_configuration,
)
from casita.bootstrap import ApplicationConfiguration, build_application
from casita.domain import HouseholdTask, MealPlanEntry, MealPlanEntryType
from casita.integrations import (
    Capability,
    CapabilityData,
    IntegrationDescriptor,
    IntegrationSnapshot,
    ReadRequest,
)
from casita.integrations.grocy.mapping import map_meal_plan, map_tasks, rows_by_id


class ProjectionTests(TestCase):
    def test_maps_recipe_product_note_and_decimal_values(self):
        entries = map_meal_plan(
            "home",
            [
                {"id": 1, "day": "2026-10-20", "section_id": 2, "type": "recipe", "recipe_id": 3, "recipe_servings": "1.25", "done": 0},
                {"id": 2, "day": "2026-10-20", "section_id": 2, "type": "product", "product_id": 4, "product_amount": "0.333", "product_qu_id": 5, "done": 1},
                {"id": 3, "day": "2026-10-21", "section_id": 2, "type": "note", "note": "Leftovers", "done": 0},
            ],
            rows_by_id([{"id": 2, "name": "Dinner"}]),
            rows_by_id([{"id": 3, "name": "Tacos", "description": "Family dinner"}]),
            rows_by_id([{"id": 4, "name": "Apples"}]),
            rows_by_id([{"id": 5, "name": "Each"}]),
        )

        by_type = {entry.entry_type: entry for entry in entries}
        self.assertEqual(
            by_type[MealPlanEntryType.RECIPE].servings,
            Decimal("1.25"),
        )
        self.assertEqual(
            by_type[MealPlanEntryType.PRODUCT].quantity,
            Decimal("0.333"),
        )
        self.assertEqual(by_type[MealPlanEntryType.PRODUCT].unit, "Each")
        self.assertTrue(by_type[MealPlanEntryType.PRODUCT].completed)
        self.assertEqual(
            by_type[MealPlanEntryType.NOTE].description,
            "Leftovers",
        )

    def test_missing_reference_is_explicit_and_empty_plan_is_supported(self):
        entries = map_meal_plan(
            "home",
            [{"id": 1, "day": "2026-10-20", "section_id": 2, "type": "recipe", "recipe_id": 99}],
            rows_by_id([{"id": 2, "name": "Dinner"}]),
            {},
            {},
            {},
        )
        self.assertFalse(entries[0].reference_available)
        self.assertEqual(entries[0].title, "")
        self.assertEqual(map_meal_plan("home", [], {}, {}, {}, {}), ())

    def test_rejects_malformed_meal_plan(self):
        with self.assertRaisesRegex(ValueError, "missing its day"):
            map_meal_plan("home", [{"id": 1, "type": "note"}], {}, {}, {}, {})

    def test_maps_pending_completed_and_optional_tasks(self):
        tasks = map_tasks(
            "home",
            [
                {"id": 1, "name": "Filter", "description": "Replace", "due_date": "2026-11-01", "category_id": 3, "done": 0},
                {"id": 2, "name": "Done task", "description": None, "due_date": None, "category_id": None, "done": 1},
            ],
            rows_by_id([{"id": 3, "name": "Maintenance"}]),
        )
        self.assertEqual(tasks[0].due_on, date(2026, 11, 1))
        self.assertEqual(tasks[0].category, "Maintenance")
        self.assertTrue(tasks[1].completed)
        self.assertEqual(tasks[1].category, "")
        self.assertEqual(map_tasks("home", [], {}), ())


class FakeIntegration:
    descriptor = IntegrationDescriptor(
        key="fake",
        display_name="Fake",
        capabilities=frozenset(Capability),
    )

    def health(self):
        raise NotImplementedError

    def read(self, request: ReadRequest):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        records = ()
        if Capability.MEAL_PLAN in request.capabilities:
            records = (
                MealPlanEntry(
                    id="meal-1", household_id=request.household_id,
                    day=date(2026, 10, 20), section="Dinner",
                    entry_type=MealPlanEntryType.RECIPE, title="Tacos",
                    servings=Decimal("1.50"),
                ),
            )
        elif Capability.TASKS in request.capabilities:
            records = (
                HouseholdTask(
                    id="task-1", household_id=request.household_id,
                    name="Replace filter", due_on=date(2026, 11, 1),
                ),
            )
        capability = next(iter(request.capabilities))
        return IntegrationSnapshot(
            integration_key="fake", household_id=request.household_id,
            generated_at=now,
            data=(CapabilityData(capability, records, now),),
        )


class FailingIntegration(FakeIntegration):
    def read(self, request: ReadRequest):
        raise TimeoutError("secret upstream detail")


def configured_application(integration=None):
    integration = integration or FakeIntegration()
    owners = {capability: ("fake",) for capability in Capability}
    app = build_application(integrations=(integration,), capability_owners=owners)
    config = ApplicationConfiguration(
        project_root=os.path.abspath("."), source=None,
        grocy_url="http://grocy", grocy_api_key="hidden",
        timezone="UTC", household_id="home", household_name="Our Home",
    )
    return replace(app, configuration=config)


class ApiTests(TestCase):
    def setUp(self):
        config = DashboardApiConfiguration(
            password="correct horse battery", session_secret="s" * 32,
            cookie_secure=False,
        )
        self.client = TestClient(create_dashboard_api(configured_application(), config))

    def login(self, password="correct horse battery"):
        return self.client.post("/api/v1/session", json={"password": password})

    def test_health_is_public_but_data_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/health").status_code, 200)
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("hidden", response.text)

    def test_invalid_and_valid_login(self):
        self.assertEqual(self.login("wrong password").status_code, 401)
        response = self.login()
        self.assertEqual(response.status_code, 204)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)

    def test_read_endpoints_are_stable_and_decimal_safe(self):
        self.login()
        meal = self.client.get("/api/v1/meal-plan")
        tasks = self.client.get("/api/v1/tasks")
        dashboard = self.client.get("/api/v1/dashboard")

        self.assertEqual(meal.status_code, 200)
        self.assertEqual(meal.json()["data"][0]["servings"], "1.50")
        self.assertEqual(tasks.json()["data"][0]["due_on"], "2026-11-01")
        self.assertIn("meal_plan", dashboard.json()["data"])
        self.assertIn("tasks", dashboard.json()["data"])

    def test_transport_is_read_only(self):
        self.login()
        self.assertEqual(self.client.post("/api/v1/tasks").status_code, 405)
        self.assertEqual(self.client.delete("/api/v1/meal-plan").status_code, 405)

    def test_upstream_timeout_is_degraded_without_detail_leakage(self):
        config = DashboardApiConfiguration(
            password="correct horse battery", session_secret="s" * 32,
            cookie_secure=False,
        )
        client = TestClient(
            create_dashboard_api(configured_application(FailingIntegration()), config)
        )
        client.post(
            "/api/v1/session",
            json={"password": "correct horse battery"},
        )
        response = client.get("/api/v1/tasks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "degraded")
        self.assertNotIn("secret upstream detail", response.text)

        dashboard = client.get("/api/v1/dashboard")
        self.assertEqual(dashboard.json()["state"], "degraded")
        self.assertTrue(dashboard.json()["data"]["stale_sections"])
        self.assertNotIn("secret upstream detail", dashboard.text)

    def test_missing_application_configuration_fails_closed(self):
        app = build_application()
        config = DashboardApiConfiguration("password long enough", "s" * 32)
        with self.assertRaisesRegex(RuntimeError, "requires application configuration"):
            create_dashboard_api(app, config)

    def test_api_configuration_requires_strong_secrets(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CASITA_API_PASSWORD"):
                load_dashboard_api_configuration()

    def test_serialization_handles_empty_optional_and_datetime_values(self):
        self.assertEqual(json_value(Decimal("1.2300")), "1.2300")
        self.assertEqual(json_value(date(2026, 10, 20)), "2026-10-20")
        self.assertIsNone(json_value(None))
