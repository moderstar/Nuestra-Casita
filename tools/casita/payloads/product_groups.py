"""
Product Group payload builders.

This module converts rows from catalog/product_groups.csv into payloads
accepted by the Grocy Product Groups API.
"""

from typing import Any


def normalize_text(value: Any) -> str:
    """Convert a value to a trimmed string."""

    if value is None:
        return ""

    return str(value).strip()


def parse_active(value: Any) -> int:
    """Convert a catalog Active value to the integer expected by Grocy."""

    text = normalize_text(value).casefold()

    if text in ("", "1", "true", "yes", "active"):
        return 1

    if text in ("0", "false", "no", "inactive"):
        return 0

    raise ValueError(
        f"Active must be 1 or 0, received {value!r}."
    )


def build_product_group_create_payload(
    catalog_product_group: dict[str, Any],
) -> dict[str, Any]:
    """Build a payload for creating a Grocy Product Group."""

    name = normalize_text(
        catalog_product_group.get("Product Group")
    )

    if name == "":
        raise ValueError(
            "Product Group catalog field cannot be blank."
        )

    return {
        "name": name,
        "description": normalize_text(
            catalog_product_group.get("Description")
        ),
        "active": parse_active(
            catalog_product_group.get("Active")
        ),
    }


def build_product_group_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a Product Group payload containing only changed fields."""

    name = normalize_text(
        plan_item.get("name")
    ) or "Unknown product group"
    changes = plan_item.get("changes")

    if not isinstance(changes, list):
        raise ValueError(
            f"{name}: update plan changes must be a list."
        )

    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{name}: every update change must be a dictionary."
            )

        api_field = normalize_text(
            change.get("api_field")
        )

        if api_field == "":
            raise ValueError(
                f"{name}: an update change is missing api_field."
            )

        if "catalog_value" not in change:
            raise ValueError(
                f"{name}: change for {api_field!r} "
                "is missing catalog_value."
            )

        payload[api_field] = change["catalog_value"]

    if not payload:
        raise ValueError(
            f"{name}: no Product Group update fields were generated."
        )

    return payload
