"""
Battery payload builders.

This module converts rows from catalog/batteries.csv into payloads accepted
by the Grocy Batteries API.
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


def parse_charge_interval_days(value: Any) -> int:
    """Convert a catalog charge interval to a nonnegative integer."""

    text = normalize_text(value)

    if text == "":
        return 0

    try:
        interval = int(text)
    except ValueError as error:
        raise ValueError(
            "Charge Interval Days must be a nonnegative integer, "
            f"received {value!r}."
        ) from error

    if interval < 0:
        raise ValueError(
            "Charge Interval Days cannot be negative, "
            f"received {value!r}."
        )

    return interval


def build_battery_create_payload(
    catalog_battery: dict[str, Any],
) -> dict[str, Any]:
    """Build a payload for creating a Grocy Battery."""

    name = normalize_text(
        catalog_battery.get("Battery")
    )

    if name == "":
        raise ValueError(
            "Battery catalog field cannot be blank."
        )

    return {
        "name": name,
        "description": normalize_text(
            catalog_battery.get("Description")
        ),
        "used_in": normalize_text(
            catalog_battery.get("Used In")
        ),
        "charge_interval_days": parse_charge_interval_days(
            catalog_battery.get("Charge Interval Days")
        ),
        "active": parse_active(
            catalog_battery.get("Active")
        ),
    }


def build_battery_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a Battery payload containing only changed fields."""

    name = normalize_text(
        plan_item.get("name")
    ) or "Unknown battery"
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
            f"{name}: no Battery update fields were generated."
        )

    return payload
