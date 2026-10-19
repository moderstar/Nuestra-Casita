"""Grocy Equipment synchronization resource."""

from typing import Any

from casita.payloads import (
    build_equipment_create_payload,
    build_equipment_update_payload,
)


def display_value(value: Any) -> str:
    """Convert an Equipment value into clean display text."""

    if value is None:
        return ""

    return str(value).strip()


def compare_equipment(
    catalog_equipment: dict[str, Any],
    grocy_equipment: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare only the safely Git-owned description field."""

    del lookups
    catalog_value = display_value(catalog_equipment.get("Description"))
    grocy_value = display_value(grocy_equipment.get("description"))

    if catalog_value == grocy_value:
        return []

    return [{
        "label": "Description",
        "api_field": "description",
        "grocy_display": grocy_value,
        "catalog_display": catalog_value,
        "grocy_value": grocy_value,
        "catalog_value": catalog_value,
    }]


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Adapt an Equipment create item to the generic apply interface."""

    del lookups
    catalog_equipment = plan_item.get("catalog")

    if not isinstance(catalog_equipment, dict):
        raise ValueError("Equipment create plan item has no valid catalog row.")

    return build_equipment_create_payload(catalog_equipment)


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Adapt a safe Equipment update to the generic apply interface."""

    del lookups
    return build_equipment_update_payload(plan_item)


EQUIPMENT_RESOURCE = {
    "name": "equipment",
    "singular_name": "equipment item",
    "plural_name": "equipment",
    "catalog_file": "equipment.csv",
    "catalog_name_field": "Equipment",
    "grocy_endpoint": "/objects/equipment",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_equipment,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
