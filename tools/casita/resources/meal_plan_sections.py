"""Grocy Meal Plan Sections synchronization resource."""

from typing import Any, Callable

from casita.payloads import (
    build_meal_plan_section_create_payload,
    build_meal_plan_section_update_payload,
    parse_meal_plan_section_sort_number,
    parse_meal_plan_section_time,
)


def display_value(value: Any) -> str:
    """Convert a section value to display text."""

    if value is None:
        return ""

    return str(value).strip()


def normalize_optional_integer(value: Any) -> int | None:
    """Normalize an optional native integer."""

    return parse_meal_plan_section_sort_number(value)


def normalize_optional_time(value: Any) -> str | None:
    """Normalize Grocy's optional HH:MM or HH:MM:SS time."""

    text = display_value(value)

    if text == "":
        return None

    if len(text) == 8 and text.endswith(":00"):
        text = text[:5]

    return parse_meal_plan_section_time(text)


def compare_meal_plan_section(
    catalog_section: dict[str, Any],
    grocy_section: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare Git-owned section presentation fields."""

    del lookups
    fields: tuple[tuple[str, str, Any, Callable[[Any], Any]], ...] = (
        (
            "Sort Number",
            "sort_number",
            parse_meal_plan_section_sort_number(
                catalog_section.get("Sort Number")
            ),
            normalize_optional_integer,
        ),
        (
            "Time",
            "time_info",
            parse_meal_plan_section_time(catalog_section.get("Time")),
            normalize_optional_time,
        ),
    )
    differences = []

    for label, api_field, catalog_value, normalize_grocy in fields:
        grocy_value = normalize_grocy(grocy_section.get(api_field))

        if catalog_value != grocy_value:
            differences.append(
                {
                    "label": label,
                    "api_field": api_field,
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
    """Build a Meal Plan Section create payload."""

    del lookups
    catalog_section = plan_item.get("catalog")

    if not isinstance(catalog_section, dict):
        raise ValueError("Section create plan item has no valid catalog row.")

    return build_meal_plan_section_create_payload(catalog_section)


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Meal Plan Section update payload."""

    del lookups
    return build_meal_plan_section_update_payload(plan_item)


MEAL_PLAN_SECTION_RESOURCE = {
    "name": "meal-plan-sections",
    "singular_name": "meal plan section",
    "plural_name": "meal plan sections",
    "catalog_file": "meal_plan_sections.csv",
    "catalog_name_field": "Meal Plan Section",
    "grocy_endpoint": "/objects/meal_plan_sections?query[]=id>0",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_meal_plan_section,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
