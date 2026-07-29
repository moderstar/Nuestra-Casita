"""
Shopping Locations resource definition.

This module describes how catalog/stores.csv maps to Grocy Shopping Locations
and adapts its payload builders to the generic apply-engine interface.
"""

from typing import Any

from casita.payloads import (
    build_shopping_location_create_payload,
    build_shopping_location_update_payload,
    parse_shopping_location_active,
)


def display_value(value: Any) -> str:
    """Convert a Shopping Location value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def compare_shopping_location(
    catalog_shopping_location: dict[str, Any],
    grocy_shopping_location: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Shopping Location with its Grocy object."""

    del lookups

    fields = (
        {
            "label": "Description",
            "catalog_key": "Description",
            "api_field": "description",
            "normalize": display_value,
        },
        {
            "label": "Active",
            "catalog_key": "Active",
            "api_field": "active",
            "normalize": parse_shopping_location_active,
        },
    )
    differences = []

    for field in fields:
        catalog_raw = catalog_shopping_location.get(
            field["catalog_key"]
        )
        grocy_raw = grocy_shopping_location.get(
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
    """Build a Shopping Location create payload from a generic plan item."""

    del lookups
    name = str(
        plan_item.get("name") or "Unknown shopping location"
    ).strip()
    catalog_shopping_location = plan_item.get("catalog")

    if not isinstance(catalog_shopping_location, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_shopping_location_create_payload(
        catalog_shopping_location
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Shopping Location update payload from a generic plan item."""

    del lookups
    return build_shopping_location_update_payload(plan_item)


SHOPPING_LOCATION_RESOURCE = {
    "name": "shopping-locations",
    "singular_name": "shopping location",
    "plural_name": "shopping locations",
    "catalog_file": "stores.csv",
    "catalog_name_field": "Store",
    "grocy_endpoint": "/objects/shopping_locations",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_shopping_location,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
