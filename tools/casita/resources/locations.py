"""
Locations resource definition.

This module describes how catalog/locations.csv maps to Grocy Locations and
adapts its payload builders to the generic apply-engine interface.
"""

from typing import Any

from casita.payloads import (
    build_location_create_payload,
    build_location_update_payload,
    parse_location_active,
    parse_location_is_freezer,
)


def display_value(value: Any) -> str:
    """Convert a Location value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def compare_location(
    catalog_location: dict[str, Any],
    grocy_location: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Location with its Grocy object."""

    del lookups

    fields = (
        {
            "label": "Description",
            "catalog_key": "Description",
            "api_field": "description",
            "normalize": display_value,
        },
        {
            "label": "Is Freezer",
            "catalog_key": "Is Freezer",
            "api_field": "is_freezer",
            "normalize": parse_location_is_freezer,
        },
        {
            "label": "Active",
            "catalog_key": "Active",
            "api_field": "active",
            "normalize": parse_location_active,
        },
    )
    differences = []

    for field in fields:
        catalog_raw = catalog_location.get(
            field["catalog_key"]
        )
        grocy_raw = grocy_location.get(
            field["api_field"]
        )
        normalize = field["normalize"]
        catalog_value = normalize(catalog_raw)
        grocy_value = normalize(grocy_raw)

        if catalog_value != grocy_value:
            differences.append(
                {
                    "label": field["label"],
                    "api_field": field["api_field"],
                    "grocy_display": display_value(grocy_value),
                    "catalog_display": display_value(catalog_value),
                    "grocy_value": grocy_value,
                    "catalog_value": catalog_value,
                }
            )

    return differences


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Location create payload from a generic plan item."""

    del lookups
    name = str(
        plan_item.get("name") or "Unknown location"
    ).strip()
    catalog_location = plan_item.get("catalog")

    if not isinstance(catalog_location, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_location_create_payload(
        catalog_location
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Location update payload from a generic plan item."""

    del lookups
    return build_location_update_payload(plan_item)


LOCATION_RESOURCE = {
    "name": "locations",
    "singular_name": "location",
    "plural_name": "locations",
    "catalog_file": "locations.csv",
    "catalog_name_field": "Location",
    "grocy_endpoint": "/objects/locations",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_location,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
