"""
Product Groups resource definition.

This module describes how catalog/product_groups.csv maps to Grocy Product
Groups and adapts its payload builders to the generic apply-engine interface.
"""

from typing import Any

from casita.payloads import (
    build_product_group_create_payload,
    build_product_group_update_payload,
    parse_product_group_active,
)


def display_value(value: Any) -> str:
    """Convert a Product Group value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def compare_product_group(
    catalog_product_group: dict[str, Any],
    grocy_product_group: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Product Group with its Grocy object."""

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
            "normalize": parse_product_group_active,
        },
    )
    differences = []

    for field in fields:
        catalog_raw = catalog_product_group.get(
            field["catalog_key"]
        )
        grocy_raw = grocy_product_group.get(
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
    """Build a Product Group create payload from a generic plan item."""

    del lookups
    name = str(
        plan_item.get("name") or "Unknown product group"
    ).strip()
    catalog_product_group = plan_item.get("catalog")

    if not isinstance(catalog_product_group, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_product_group_create_payload(
        catalog_product_group
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Product Group update payload from a generic plan item."""

    del lookups
    return build_product_group_update_payload(plan_item)


PRODUCT_GROUP_RESOURCE = {
    "name": "product-groups",
    "singular_name": "product group",
    "plural_name": "product groups",
    "catalog_file": "product_groups.csv",
    "catalog_name_field": "Product Group",
    "grocy_endpoint": "/objects/product_groups",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_product_group,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
