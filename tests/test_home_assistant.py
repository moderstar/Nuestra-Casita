"""Tests for the read-only Home Assistant integration."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

from casita.api import DashboardApiConfiguration, create_dashboard_api
from casita.bootstrap import (
    ApplicationConfiguration,
    build_application,
    build_grocy_application,
    load_configuration,
)
from casita.dashboard import DashboardSection
from casita.domain import DeviceState, Household
from casita.integrations import Capability, ReadRequest
from casita.integrations.home_assistant import (
    HomeAssistantApiClient,
    HomeAssistantApiError,
    HomeAssistantAuthenticationError,
    HomeAssistantReadAdapter,
    HomeAssistantResponseError,
)


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, json_error=None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class RecordingSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, *, headers, timeout):
        self.calls.append((url, headers, timeout))
        if self.error is not None:
            raise self.error
        return self.response


class HomeAssistantClientTests(TestCase):
    def test_authenticated_read_uses_bearer_token_and_timeout(self):
        session = RecordingSession(FakeResponse([]))
        client = HomeAssistantApiClient(
            "http://home-assistant:8123/", "top-secret", timeout=4.5,
            session=session,
        )

        self.assertEqual(client.get_states(), [])
        url, headers, timeout = session.calls[0]
        self.assertEqual(url, "http://home-assistant:8123/api/states")
        self.assertEqual(headers["Authorization"], "Bearer top-secret")
        self.assertEqual(timeout, 4.5)

    def test_health_uses_the_required_trailing_slash_api_root(self):
        session = RecordingSession(FakeResponse({"message": "API running."}))
        client = HomeAssistantApiClient(
            "http://home-assistant:8123", "top-secret", session=session
        )
        client.get_root()
        self.assertEqual(session.calls[0][0], "http://home-assistant:8123/api/")

    def test_authentication_connection_timeout_and_json_failures_are_safe(self):
        cases = (
            (
                RecordingSession(FakeResponse({}, status_code=401)),
                HomeAssistantAuthenticationError,
            ),
            (
                RecordingSession(error=requests.ConnectionError("secret URL")),
                HomeAssistantApiError,
            ),
            (
                RecordingSession(error=requests.Timeout("secret token")),
                TimeoutError,
            ),
            (
                RecordingSession(FakeResponse(json_error=ValueError("raw body"))),
                HomeAssistantResponseError,
            ),
        )
        for session, expected in cases:
            with self.subTest(expected=expected):
                client = HomeAssistantApiClient(
                    "http://home-assistant:8123", "hidden", session=session
                )
                with self.assertRaises(expected) as raised:
                    client.get_states()
                self.assertNotIn("secret", str(raised.exception))
                self.assertNotIn("hidden", str(raised.exception))

    def test_states_response_must_be_a_list(self):
        client = HomeAssistantApiClient(
            "http://home-assistant:8123", "hidden",
            session=RecordingSession(FakeResponse({"message": "API running."})),
        )
        with self.assertRaises(HomeAssistantResponseError):
            client.get_states()


class FakeHomeAssistant:
    def __init__(self, states=(), error=None):
        self.states = list(states)
        self.error = error
        self.root_calls = 0
        self.state_calls = 0

    def get_root(self):
        self.root_calls += 1
        if self.error is not None:
            raise self.error
        return {"message": "API running."}

    def get_states(self):
        self.state_calls += 1
        if self.error is not None:
            raise self.error
        return self.states


STATES = (
    {
        "entity_id": "sensor.kitchen_temperature",
        "state": "72.4",
        "attributes": {
            "friendly_name": "Kitchen Temperature",
            "unit_of_measurement": "°F",
            "device_class": "temperature",
            "latitude": "must-not-be-exposed",
        },
    },
    {
        "entity_id": "binary_sensor.garage_door",
        "state": "unavailable",
        "attributes": {"friendly_name": "Garage Door"},
    },
    {
        "entity_id": "sensor.weather_summary",
        "state": "unknown",
        "attributes": {"friendly_name": "Weather Summary"},
    },
    {
        "entity_id": "person.private_location",
        "state": "home",
        "attributes": {"friendly_name": "Private Location"},
    },
)


class HomeAssistantAdapterTests(TestCase):
    def setUp(self):
        self.client = FakeHomeAssistant(STATES)
        self.adapter = HomeAssistantReadAdapter(
            self.client,
            entity_ids=(
                "sensor.kitchen_temperature",
                "binary_sensor.garage_door",
                "sensor.weather_summary",
                "light.missing",
            ),
        )

    def read(self):
        return self.adapter.read(
            ReadRequest("home", frozenset({Capability.DEVICES}))
        ).data[0].records

    def test_normalizes_allowlisted_states_units_domains_and_availability(self):
        records = self.read()
        self.assertEqual(len(records), 4)
        by_name = {record.name: record for record in records}
        temperature = by_name["Kitchen Temperature"]
        self.assertEqual(temperature.kind, "sensor")
        self.assertEqual(temperature.value, "72.4")
        self.assertEqual(temperature.unit, "°F")
        self.assertEqual(temperature.state, DeviceState.AVAILABLE)
        self.assertEqual(temperature.attributes, (("device_class", "temperature"),))
        self.assertEqual(
            temperature.source_references[0].external_id,
            "sensor.kitchen_temperature",
        )
        self.assertEqual(by_name["Garage Door"].state, DeviceState.UNAVAILABLE)
        self.assertEqual(by_name["Weather Summary"].state, DeviceState.UNKNOWN)
        self.assertEqual(by_name["missing"].state, DeviceState.UNAVAILABLE)

    def test_does_not_expose_entities_outside_the_allowlist(self):
        records = self.read()
        external_ids = {
            record.source_references[0].external_id for record in records
        }
        self.assertNotIn("person.private_location", external_ids)

    def test_empty_allowlist_is_safe_and_performs_no_state_request(self):
        adapter = HomeAssistantReadAdapter(self.client, entity_ids=())
        snapshot = adapter.read(
            ReadRequest("home", frozenset({Capability.DEVICES}))
        )
        self.assertEqual(snapshot.data[0].records, ())
        self.assertEqual(self.client.state_calls, 0)

    def test_malformed_entity_rows_fail_the_capability_read(self):
        adapter = HomeAssistantReadAdapter(
            FakeHomeAssistant(({"entity_id": "sensor.bad"},)),
            entity_ids=("sensor.bad",),
        )
        with self.assertRaisesRegex(ValueError, "malformed"):
            adapter.read(ReadRequest("home", frozenset({Capability.DEVICES})))

    def test_health_reports_safe_availability(self):
        self.assertEqual(self.adapter.health().status.value, "healthy")
        failed = HomeAssistantReadAdapter(
            FakeHomeAssistant(error=RuntimeError("http://private token")),
            entity_ids=(),
        ).health()
        self.assertEqual(failed.status.value, "unavailable")
        self.assertNotIn("private", failed.message)
        self.assertNotIn("token", failed.message)


class HomeAssistantConfigurationTests(TestCase):
    def test_missing_optional_configuration_disables_integration(self):
        with patch.dict(os.environ, {}, clear=True):
            config = load_configuration(strict=False)
        self.assertFalse(config.home_assistant_configured)
        self.assertEqual(config.home_assistant_entity_ids, ())

    def test_parses_allowlist_and_rejects_partial_or_invalid_configuration(self):
        environment = {
            "HOME_ASSISTANT_URL": "http://home-assistant:8123",
            "HOME_ASSISTANT_TOKEN": "secret",
            "HOME_ASSISTANT_ENTITY_IDS": "sensor.one, light.two, sensor.one",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = load_configuration(strict=False)
        self.assertEqual(
            config.home_assistant_entity_ids,
            ("sensor.one", "light.two"),
        )
        with patch.dict(
            os.environ,
            {"HOME_ASSISTANT_URL": "http://home-assistant:8123"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "configured together"):
                load_configuration(strict=False)
        with patch.dict(
            os.environ,
            {
                "HOME_ASSISTANT_URL": "http://home-assistant:8123",
                "HOME_ASSISTANT_TOKEN": "secret",
                "HOME_ASSISTANT_ENTITY_IDS": "not-an-entity",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "entity IDs"):
                load_configuration(strict=False)
        with patch.dict(
            os.environ,
            {"CASITA_REQUEST_TIMEOUT_SECONDS": "0"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "between 0.1 and 60"):
                load_configuration(strict=False)

    def test_composition_registers_devices_only_when_configured(self):
        common = dict(
            project_root=os.path.abspath("."), source=None,
            grocy_url="http://grocy", grocy_api_key="hidden",
            timezone="UTC", household_id="home", household_name="Our Home",
        )
        disabled = build_grocy_application(
            configuration=ApplicationConfiguration(**common)
        )
        self.assertEqual(
            disabled.integrations.integrations_for(Capability.DEVICES), ()
        )
        enabled = build_grocy_application(
            configuration=ApplicationConfiguration(
                **common,
                home_assistant_url="http://home-assistant:8123",
                home_assistant_token="hidden",
                home_assistant_entity_ids=("sensor.kitchen_temperature",),
            )
        )
        devices = enabled.integrations.integrations_for(Capability.DEVICES)
        self.assertEqual(
            tuple(item.descriptor.key for item in devices),
            ("home-assistant",),
        )


class HomeAssistantDashboardTests(TestCase):
    def configured_application(self, integration):
        app = build_application(
            integrations=(integration,),
            capability_owners={Capability.DEVICES: ("home-assistant",)},
        )
        return replace(
            app,
            configuration=ApplicationConfiguration(
                project_root=os.path.abspath("."), source=None,
                grocy_url="http://grocy", grocy_api_key="hidden",
                timezone="UTC", household_id="home", household_name="Our Home",
            ),
        )

    def test_dashboard_snapshot_contains_devices_and_isolates_outages(self):
        adapter = HomeAssistantReadAdapter(
            FakeHomeAssistant(STATES),
            entity_ids=("sensor.kitchen_temperature",),
        )
        app = self.configured_application(adapter)
        snapshot = app.dashboard.build(
            Household("home", "Our Home", "UTC"),
            now=datetime(2026, 10, 21, tzinfo=timezone.utc),
        )
        self.assertEqual(snapshot.devices[0].name, "Kitchen Temperature")
        self.assertNotIn(DashboardSection.HOME, snapshot.stale_sections)

        failing = HomeAssistantReadAdapter(
            FakeHomeAssistant(error=TimeoutError("private endpoint")),
            entity_ids=("sensor.kitchen_temperature",),
        )
        failed_snapshot = self.configured_application(failing).dashboard.build(
            Household("home", "Our Home", "UTC"),
            now=datetime(2026, 10, 21, tzinfo=timezone.utc),
        )
        self.assertEqual(failed_snapshot.devices, ())
        self.assertIn(DashboardSection.HOME, failed_snapshot.stale_sections)
        self.assertEqual(failed_snapshot.issues[0].source, "home-assistant")

    def test_devices_endpoint_is_authenticated_and_read_only(self):
        adapter = HomeAssistantReadAdapter(
            FakeHomeAssistant(STATES),
            entity_ids=("sensor.kitchen_temperature",),
        )
        app = self.configured_application(adapter)
        client = TestClient(create_dashboard_api(
            app,
            DashboardApiConfiguration(
                "correct horse battery", "s" * 32, cookie_secure=False
            ),
        ))
        self.assertEqual(client.get("/api/v1/devices").status_code, 401)
        client.post(
            "/api/v1/session",
            json={"password": "correct horse battery"},
        )
        response = client.get("/api/v1/devices")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["value"], "72.4")
        self.assertEqual(client.post("/api/v1/devices").status_code, 405)

    def test_devices_api_failure_is_degraded_without_upstream_details(self):
        adapter = HomeAssistantReadAdapter(
            FakeHomeAssistant(
                error=RuntimeError(
                    "http://192.168.8.157:8123 Bearer household-secret"
                )
            ),
            entity_ids=("sensor.kitchen_temperature",),
        )
        client = TestClient(create_dashboard_api(
            self.configured_application(adapter),
            DashboardApiConfiguration(
                "correct horse battery", "s" * 32, cookie_secure=False
            ),
        ))
        client.post(
            "/api/v1/session",
            json={"password": "correct horse battery"},
        )
        response = client.get("/api/v1/devices")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "degraded")
        self.assertEqual(response.json()["data"], [])
        self.assertNotIn("192.168.8.157", response.text)
        self.assertNotIn("household-secret", response.text)
