"""Tests for the Home Assistant Entity Manager API."""

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from casita.integrations.home_assistant.entity_manager_api import (
    create_entity_manager_router,
)


@dataclass
class Selection:
    entity_id: str
    enabled: bool
    room: str | None = None


class FakeRepository:
    def __init__(self):
        self.selections = {
            "light.kitchen": Selection("light.kitchen", True, "Kitchen"),
            "switch.office": Selection("switch.office", False, "Office"),
        }

    def list(self, household_id):
        return tuple(self.selections.values())

    def save(self, household_id, entity_id, *, enabled, room=None):
        self.selections[entity_id] = Selection(entity_id, enabled, room)


class FakeHomeAssistant:
    def get_states(self):
        return [
            {
                "entity_id": "light.kitchen",
                "state": "on",
                "attributes": {"friendly_name": "Kitchen Light"},
            },
            {
                "entity_id": "sensor.temperature",
                "state": "22",
                "attributes": {"friendly_name": "Temperature"},
            },
        ]


def test_entity_discovery_includes_saved_preferences():
    repository = FakeRepository()
    app = FastAPI()

    app.include_router(
        create_entity_manager_router(
            repository=repository,
            client=FakeHomeAssistant(),
            household_id="default",
            authenticate=lambda: None,
            verify_csrf=lambda: None,
        )
    )

    client = TestClient(app)
    response = client.get("/api/v1/home-assistant/entities")

    assert response.status_code == 200

    entities = {
        item["entity_id"]: item
        for item in response.json()["entities"]
    }

    assert entities["light.kitchen"]["enabled"] is True
    assert entities["light.kitchen"]["room"] == "Kitchen"
    assert entities["sensor.temperature"]["enabled"] is False

    # Saved entities remain visible when HA no longer reports them.
    assert entities["switch.office"]["state"] == "unavailable"
    assert entities["switch.office"]["enabled"] is False


def test_entity_updates_and_room_assignments():
    repository = FakeRepository()
    app = FastAPI()

    app.include_router(
        create_entity_manager_router(
            repository=repository,
            client=FakeHomeAssistant(),
            household_id="default",
            authenticate=lambda: None,
            verify_csrf=lambda: None,
        )
    )

    client = TestClient(app)

    # Enable an entity and assign it to a room.
    response = client.put(
        "/api/v1/home-assistant/entities/sensor.temperature",
        json={"enabled": True, "room": "Living Room"},
    )

    assert response.status_code == 200
    assert repository.selections["sensor.temperature"].enabled is True
    assert repository.selections["sensor.temperature"].room == "Living Room"

    # Disable the entity without deleting its saved preference.
    response = client.put(
        "/api/v1/home-assistant/entities/sensor.temperature",
        json={"enabled": False, "room": "Living Room"},
    )

    assert response.status_code == 200
    assert repository.selections["sensor.temperature"].enabled is False

    # Saved rooms should be discoverable.
    response = client.get("/api/v1/home-assistant/rooms")

    assert response.status_code == 200
    assert "Living Room" in response.json()["rooms"]

    # Invalid entity identifiers must be rejected.
    response = client.put(
        "/api/v1/home-assistant/entities/invalid-entity",
        json={"enabled": True},
    )

    assert response.status_code == 400


def test_entity_manager_requires_authentication_and_csrf():
    from fastapi import HTTPException

    repository = FakeRepository()
    app = FastAPI()

    def require_authentication():
        raise HTTPException(status_code=401, detail="Authentication required.")

    app.include_router(
        create_entity_manager_router(
            repository=repository,
            client=FakeHomeAssistant(),
            household_id="default",
            authenticate=require_authentication,
            verify_csrf=lambda: None,
        )
    )

    client = TestClient(app)

    assert client.get(
        "/api/v1/home-assistant/entities"
    ).status_code == 401

    assert client.get(
        "/api/v1/home-assistant/rooms"
    ).status_code == 401

    assert client.put(
        "/api/v1/home-assistant/entities/light.kitchen",
        json={"enabled": False},
    ).status_code == 401

    assert repository.selections["light.kitchen"].enabled is True

    # An authenticated request without valid CSRF must be rejected.
    protected_app = FastAPI()

    def reject_csrf():
        raise HTTPException(status_code=403, detail="Invalid CSRF token.")

    protected_app.include_router(
        create_entity_manager_router(
            repository=repository,
            client=FakeHomeAssistant(),
            household_id="default",
            authenticate=lambda: None,
            verify_csrf=reject_csrf,
        )
    )

    protected_client = TestClient(protected_app)

    assert protected_client.put(
        "/api/v1/home-assistant/entities/light.kitchen",
        json={"enabled": False},
    ).status_code == 403

    assert repository.selections["light.kitchen"].enabled is True


def test_nonexistent_entity_cannot_be_saved():
    repository = FakeRepository()
    app = FastAPI()

    app.include_router(
        create_entity_manager_router(
            repository=repository,
            client=FakeHomeAssistant(),
            household_id="default",
            authenticate=lambda: None,
            verify_csrf=lambda: None,
        )
    )

    client = TestClient(app)

    # A valid-looking but nonexistent entity must be rejected.
    response = client.put(
        "/api/v1/home-assistant/entities/switch.nonexistent_device",
        json={"enabled": True, "room": "Office"},
    )

    assert response.status_code == 404
    assert "switch.nonexistent_device" not in repository.selections

    # An existing saved entity must remain editable even when
    # Home Assistant no longer reports it.
    response = client.put(
        "/api/v1/home-assistant/entities/switch.office",
        json={"enabled": True, "room": "Office"},
    )

    assert response.status_code == 200
    assert repository.selections["switch.office"].enabled is True
