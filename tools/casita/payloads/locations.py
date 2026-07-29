"""
Location payload builders.

This module converts rows from catalog/locations.csv into payloads accepted
by the Grocy Locations API.
"""

from typing import Any


def normalize_text(value: Any) -> str:
    """Convert a value to a trimmed string."""

    if value is None:
        return ""

    return str(value).strip()


def parse_boolean(value: Any, field_name: str) -> int:
    """Convert a catalog boolean value to the integer expected by Grocy."""

    text = normalize_text(value).casefold()

    if text in ("", "0", "false", "no"):
        return 0

    if text in ("1", "true", "yes"):
        return 1

    raise ValueError(
        f"{field_name} must be 1 or 0, received {value!r}."
    )


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


def parse_is_freezer(value: Any) -> int:
    """Convert a catalog Is Freezer value to the integer expected by Grocy."""

    return parse_boolean(value, "Is Freezer")


def build_location_create_payload(
    catalog_location: dict[str, Any],
) -> dict[str, Any]:
    """Build a payload for creating a Grocy Location."""

    name = normalize_text(
        catalog_location.get("Location")
    )

    if name == "":
        raise ValueError(
            "Location catalog field cannot be blank."
        )

    return {
        "name": name,
        "description": normalize_text(
            catalog_location.get("Description")
        ),
        "is_freezer": parse_is_freezer(
            catalog_location.get("Is Freezer")
        ),
        "active": parse_active(
            catalog_location.get("Active")
        ),
    }


def build_location_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a Location payload containing only changed fields."""

    name = normalize_text(
        plan_item.get("name")
    ) or "Unknown location"
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
            f"{name}: no Location update fields were generated."
        )

    return payload
