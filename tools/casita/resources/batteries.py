"""
Batteries resource definition.

This module describes how catalog/batteries.csv maps to native Grocy 4.6
Batteries and adapts its payload builders to the generic apply-engine
interface.
"""

from typing import Any

from casita.payloads import (
    build_battery_create_payload,
    build_battery_update_payload,
    parse_battery_active,
    parse_battery_charge_interval_days,
)


def display_value(value: Any) -> str:
    """Convert a Battery value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def compare_battery(
    catalog_battery: dict[str, Any],
    grocy_battery: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Battery with its Grocy object."""

    del lookups

    fields = (
        {
            "label": "Description",
            "catalog_key": "Description",
            "api_field": "description",
            "normalize": display_value,
        },
        {
            "label": "Used In",
            "catalog_key": "Used In",
            "api_field": "used_in",
            "normalize": display_value,
        },
        {
            "label": "Charge Interval Days",
            "catalog_key": "Charge Interval Days",
            "api_field": "charge_interval_days",
            "normalize": parse_battery_charge_interval_days,
        },
        {
            "label": "Active",
            "catalog_key": "Active",
            "api_field": "active",
            "normalize": parse_battery_active,
        },
    )
    differences = []

    for field in fields:
        catalog_raw = catalog_battery.get(
            field["catalog_key"]
        )
        grocy_raw = grocy_battery.get(
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
    """Build a Battery create payload from a generic plan item."""

    del lookups
    name = str(
        plan_item.get("name") or "Unknown battery"
    ).strip()
    catalog_battery = plan_item.get("catalog")

    if not isinstance(catalog_battery, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_battery_create_payload(
        catalog_battery
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Battery update payload from a generic plan item."""

    del lookups
    return build_battery_update_payload(plan_item)


BATTERY_RESOURCE = {
    "name": "batteries",
    "singular_name": "battery",
    "plural_name": "batteries",
    "catalog_file": "batteries.csv",
    "catalog_name_field": "Battery",
    "grocy_endpoint": "/objects/batteries",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_battery,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
