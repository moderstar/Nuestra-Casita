"""Grocy task-definition synchronization resource."""

from datetime import datetime
from typing import Any, Callable

from casita.payloads import (
    build_task_create_payload,
    build_task_update_payload,
    parse_task_due_date,
    resolve_task_category_id,
)


def display_value(value: Any) -> str:
    """Convert a Task value into clean display text."""

    if value is None:
        return ""

    return str(value).strip()


def normalize_grocy_due_date(value: Any) -> str | None:
    """Normalize Grocy's nullable date or midnight datetime representation."""

    text = display_value(value)

    if text == "":
        return None

    for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, pattern)
        except ValueError:
            continue

        return parsed.strftime("%Y-%m-%d")

    raise ValueError(f"Grocy Task has an invalid due_date {value!r}.")


def normalize_optional_id(value: Any) -> int | None:
    """Normalize an optional native relationship identifier."""

    text = display_value(value)

    if text == "":
        return None

    try:
        return int(text)
    except ValueError as error:
        raise ValueError(
            f"Grocy Task has an invalid relationship ID {value!r}."
        ) from error


def compare_task(
    catalog_task: dict[str, Any],
    grocy_task: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare only Git-owned Task definition fields."""

    category_id = resolve_task_category_id(catalog_task, lookups)
    fields: tuple[tuple[str, str, Any, Callable[[Any], Any]], ...] = (
        (
            "Description",
            "description",
            display_value(catalog_task.get("Description")),
            display_value,
        ),
        (
            "Due Date",
            "due_date",
            parse_task_due_date(catalog_task.get("Due Date")),
            normalize_grocy_due_date,
        ),
        (
            "Task Category",
            "category_id",
            category_id,
            normalize_optional_id,
        ),
    )
    differences = []

    for label, api_field, catalog_value, normalize_grocy in fields:
        grocy_value = normalize_grocy(grocy_task.get(api_field))

        if catalog_value == grocy_value:
            continue

        grocy_display = display_value(grocy_value)
        catalog_display = display_value(catalog_value)

        if api_field == "category_id":
            grocy_display = display_value(
                lookups.get("task_categories_by_id", {}).get(grocy_value)
            )
            catalog_display = display_value(catalog_task.get("Task Category"))

        differences.append(
            {
                "label": label,
                "api_field": api_field,
                "grocy_display": grocy_display,
                "catalog_display": catalog_display,
                "grocy_value": grocy_value,
                "catalog_value": catalog_value,
            }
        )

    return differences


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Task create payload from a generic plan item."""

    catalog_task = plan_item.get("catalog")

    if not isinstance(catalog_task, dict):
        raise ValueError("Task create plan item has no valid catalog row.")

    return build_task_create_payload(catalog_task, lookups)


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Task definition-only update payload."""

    del lookups
    return build_task_update_payload(plan_item)


TASK_RESOURCE = {
    "name": "tasks",
    "singular_name": "task",
    "plural_name": "tasks",
    "catalog_file": "tasks.csv",
    "catalog_name_field": "Task",
    "grocy_endpoint": "/objects/tasks",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_task,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": True,
}
