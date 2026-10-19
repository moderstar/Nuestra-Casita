"""Payload and validation helpers for Grocy task definitions."""

from datetime import datetime
from typing import Any

from casita.payloads.products import find_lookup_id


def normalize_text(value: Any) -> str:
    """Convert a value to trimmed text."""

    if value is None:
        return ""

    return str(value).strip()


def parse_due_date(value: Any) -> str | None:
    """Validate an optional date-only Grocy task due date."""

    text = normalize_text(value)

    if text == "":
        return None

    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(
            "Due Date must use YYYY-MM-DD format or be blank, "
            f"received {value!r}."
        ) from error

    return text


def resolve_category_id(
    task: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> int | None:
    """Resolve an optional Task Category name."""

    task_name = normalize_text(task.get("Task")) or "Unknown task"
    category_name = normalize_text(task.get("Task Category"))

    if category_name == "":
        return None

    try:
        categories = lookups["task_categories"]
    except KeyError as error:
        raise KeyError(
            "Task Category lookup table 'task_categories' is missing."
        ) from error

    return find_lookup_id(
        categories,
        category_name,
        lookup_label="Task Category",
        product_name=task_name,
    )


def build_task_create_payload(
    task: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Task payload containing definition fields only."""

    name = normalize_text(task.get("Task"))

    if name == "":
        raise ValueError("Task catalog field cannot be blank.")

    return {
        "name": name,
        "description": normalize_text(task.get("Description")),
        "due_date": parse_due_date(task.get("Due Date")),
        "category_id": resolve_category_id(task, lookups),
    }


def build_task_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build an update containing only explicitly managed definition fields."""

    name = normalize_text(plan_item.get("name")) or "Unknown task"
    changes = plan_item.get("changes")
    managed_fields = {"description", "due_date", "category_id"}

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
                f"{name}: task field {api_field!r} is not safely managed."
            )

        if "catalog_value" not in change:
            raise ValueError(
                f"{name}: change for {api_field!r} is missing catalog_value."
            )

        payload[api_field] = change["catalog_value"]

    if not payload:
        raise ValueError(f"{name}: no Task update fields were generated.")

    return payload
