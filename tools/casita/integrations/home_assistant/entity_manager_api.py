"""Authenticated Home Assistant entity management routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


ENTITY_ID_PATTERN = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")


class EntityUpdate(BaseModel):
    enabled: bool
    room: str | None = Field(default=None, max_length=100)


def create_entity_manager_router(
    *,
    repository,
    client,
    household_id: str,
    authenticate,
    verify_csrf,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/home-assistant")

    @router.get("/entities", dependencies=[Depends(authenticate)])
    def list_entities():
        try:
            saved = {
                item.entity_id: item
                for item in repository.list(household_id)
            }
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="Entity preferences are unavailable.",
            ) from error

        try:
            states = client.get_states()
        except Exception as error:
            raise HTTPException(
                status_code=502,
                detail="Home Assistant entity discovery is unavailable.",
            ) from error

        entities = []
        seen = set()

        for state in states:
            if not isinstance(state, dict):
                continue

            entity_id = state.get("entity_id")

            if (
                not isinstance(entity_id, str)
                or not ENTITY_ID_PATTERN.fullmatch(entity_id)
                or entity_id in seen
            ):
                continue

            seen.add(entity_id)
            attributes = state.get("attributes")
            if not isinstance(attributes, dict):
                attributes = {}

            preference = saved.get(entity_id)

            entities.append({
                "entity_id": entity_id,
                "name": str(
                    attributes.get("friendly_name") or entity_id
                ),
                "domain": entity_id.split(".", 1)[0],
                "state": str(state.get("state", "unknown")),
                "enabled": preference.enabled if preference else False,
                "room": preference.room if preference else None,
            })

        # Retain saved entities even when HA no longer reports them.
        for entity_id, preference in saved.items():
            if entity_id not in seen:
                entities.append({
                    "entity_id": entity_id,
                    "name": entity_id,
                    "domain": entity_id.split(".", 1)[0],
                    "state": "unavailable",
                    "enabled": preference.enabled,
                    "room": preference.room,
                })

        return {"entities": sorted(
            entities, key=lambda item: item["entity_id"]
        )}

    @router.put(
        "/entities/{entity_id}",
        dependencies=[Depends(authenticate), Depends(verify_csrf)],
    )
    def update_entity(entity_id: str, update: EntityUpdate):
        if not ENTITY_ID_PATTERN.fullmatch(entity_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid Home Assistant entity ID.",
            )

        try:
            saved_ids = {
                item.entity_id for item in repository.list(household_id)
            }
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="Entity preferences are unavailable.",
            ) from error

        if entity_id not in saved_ids:
            try:
                states = client.get_states()
            except Exception as error:
                raise HTTPException(
                    status_code=502,
                    detail="Home Assistant entity discovery is unavailable.",
                ) from error

            if not any(
                isinstance(state, dict)
                and state.get("entity_id") == entity_id
                for state in states
            ):
                raise HTTPException(
                    status_code=404,
                    detail="Home Assistant entity not found.",
                )

        room = update.room.strip() if update.room else None
        room = room or None

        try:
            repository.save(
                household_id,
                entity_id,
                enabled=update.enabled,
                room=room,
            )
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="Entity preferences could not be saved.",
            ) from error

        return {
            "entity_id": entity_id,
            "enabled": update.enabled,
            "room": room,
        }

    @router.get("/rooms", dependencies=[Depends(authenticate)])
    def list_rooms():
        try:
            rooms = sorted({
                item.room
                for item in repository.list(household_id)
                if item.room
            })
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="Rooms could not be loaded.",
            ) from error

        return {"rooms": rooms}

    return router
