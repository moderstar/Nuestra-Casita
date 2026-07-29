"""
Payload builders for Grocy product groups.
"""

from typing import Any


def build_product_group_create_payload(
    catalog_group: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """
    Build the payload required to create a Grocy product group.
    """

    del lookups

    return {
        "name": str(
            catalog_group.get("Product Group", "")
        ).strip(),
        "description": (
            str(
                catalog_group.get(
                    "Description",
                    "",
                )
            ).strip()
            or None
        ),
        "active": 1,
    }


def build_product_group_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the payload required to update a Grocy product group.
    """

    payload: dict[str, Any] = {}

    for change in plan_item["changes"]:
        payload[
            change["api_field"]
        ] = change["catalog_value"]

    return payload
