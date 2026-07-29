"""
Task Categories resource definition.

This module describes how catalog/task_categories.csv maps to Grocy Task
Categories and adapts its payload builders to the generic apply-engine
interface.
"""

from typing import Any

from casita.payloads import (
    build_task_category_create_payload,
    build_task_category_update_payload,
    parse_task_category_active,
)


def display_value(value: Any) -> str:
    """Convert a Task Category value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def compare_task_category(
    catalog_task_category: dict[str, Any],
    grocy_task_category: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Task Category with its Grocy object."""

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
            "normalize": parse_task_category_active,
        },
    )
    differences = []

    for field in fields:
        catalog_raw = catalog_task_category.get(
            field["catalog_key"]
        )
        grocy_raw = grocy_task_category.get(
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
    """Build a Task Category create payload from a generic plan item."""

    del lookups
    name = str(
        plan_item.get("name") or "Unknown task category"
    ).strip()
    catalog_task_category = plan_item.get("catalog")

    if not isinstance(catalog_task_category, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_task_category_create_payload(
        catalog_task_category
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Task Category update payload from a generic plan item."""

    del lookups
    return build_task_category_update_payload(plan_item)


TASK_CATEGORY_RESOURCE = {
    "name": "task-categories",
    "singular_name": "task category",
    "plural_name": "task categories",
    "catalog_file": "task_categories.csv",
    "catalog_name_field": "Task Category",
    "grocy_endpoint": "/objects/task_categories",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_task_category,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
