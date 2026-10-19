"""Payload helpers for Grocy meal-plan section definitions."""

from datetime import datetime
from typing import Any


def normalize_text(value: Any) -> str:
    """Convert a value to trimmed text."""

    if value is None:
        return ""

    return str(value).strip()


def parse_sort_number(value: Any) -> int | None:
    """Validate an optional nonnegative section sort number."""

    text = normalize_text(value)

    if text == "":
        return None

    try:
        number = int(text)
    except ValueError as error:
        raise ValueError(
            f"Sort Number must be a nonnegative integer, received {value!r}."
        ) from error

    if number < 0:
        raise ValueError(
            f"Sort Number must be zero or greater, received {value!r}."
        )

    return number


def parse_time_info(value: Any) -> str | None:
    """Validate an optional section presentation time."""

    text = normalize_text(value)

    if text == "":
        return None

    try:
        datetime.strptime(text, "%H:%M")
    except ValueError as error:
        raise ValueError(
            f"Time must use HH:MM 24-hour format, received {value!r}."
        ) from error

    return text


def build_meal_plan_section_create_payload(
    section: dict[str, Any],
) -> dict[str, Any]:
    """Build a validated Meal Plan Section payload."""

    name = normalize_text(section.get("Meal Plan Section"))

    if name == "":
        raise ValueError("Meal Plan Section field cannot be blank.")

    return {
        "name": name,
        "sort_number": parse_sort_number(section.get("Sort Number")),
        "time_info": parse_time_info(section.get("Time")),
    }


def build_meal_plan_section_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a section update containing only managed fields."""

    name = normalize_text(plan_item.get("name")) or "Unknown section"
    changes = plan_item.get("changes")
    managed_fields = {"sort_number", "time_info"}

    if not isinstance(changes, list):
        raise ValueError(f"{name}: update plan changes must be a list.")

    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{name}: every update change must be a dictionary."
            )

        api_field = normalize_text(change.get("api_field"))

        if api_field not in managed_fields:
            raise ValueError(
                f"{name}: section field {api_field!r} is not safely managed."
            )

        if "catalog_value" not in change:
            raise ValueError(
                f"{name}: change for {api_field!r} is missing catalog_value."
            )

        payload[api_field] = change["catalog_value"]

    if not payload:
        raise ValueError(f"{name}: no section update fields were generated.")

    return payload
