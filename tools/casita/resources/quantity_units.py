"""
Quantity Units resource definition.

This module describes how catalog/quantity_units.csv maps to Grocy Quantity
Units and adapts its payload builders to the generic apply-engine interface.
"""

from typing import Any

from casita.payloads import (
    build_quantity_unit_create_payload,
    build_quantity_unit_update_payload,
    parse_quantity_unit_active,
)


def display_value(value: Any) -> str:
    """Convert a Quantity Unit value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def compare_quantity_unit(
    catalog_quantity_unit: dict[str, Any],
    grocy_quantity_unit: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Quantity Unit with its Grocy object."""

    del lookups

    fields = (
        {
            "label": "Plural Name",
            "catalog_key": "Plural Name",
            "api_field": "name_plural",
            "normalize": display_value,
        },
        {
            "label": "Plural Forms",
            "catalog_key": "Plural Forms",
            "api_field": "plural_forms",
            "normalize": display_value,
        },
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
            "normalize": parse_quantity_unit_active,
        },
    )
    differences = []

    for field in fields:
        catalog_raw = catalog_quantity_unit.get(
            field["catalog_key"]
        )
        grocy_raw = grocy_quantity_unit.get(
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
    """Build a Quantity Unit create payload from a generic plan item."""

    del lookups
    name = str(
        plan_item.get("name") or "Unknown quantity unit"
    ).strip()
    catalog_quantity_unit = plan_item.get("catalog")

    if not isinstance(catalog_quantity_unit, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_quantity_unit_create_payload(
        catalog_quantity_unit
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Quantity Unit update payload from a generic plan item."""

    del lookups
    return build_quantity_unit_update_payload(plan_item)


QUANTITY_UNIT_RESOURCE = {
    "name": "quantity-units",
    "singular_name": "quantity unit",
    "plural_name": "quantity units",
    "catalog_file": "quantity_units.csv",
    "catalog_name_field": "Quantity Unit",
    "grocy_endpoint": "/objects/quantity_units",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_quantity_unit,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
