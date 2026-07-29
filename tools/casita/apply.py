"""
Generic execution engine for Nuestra Casita synchronization plans.

The apply engine contains no resource-specific behavior. A registered resource
provides its Grocy endpoint, object-ID field, display names, and payload
builders. Nothing in this module runs automatically; changes are sent to Grocy
only when apply_plan() is called after an explicit --apply command.
"""

from typing import Any, Callable

from casita.grocy import post, put
from casita.lookups import build_lookups


PayloadBuilder = Callable[
    [dict[str, Any], dict[str, dict[Any, Any]]],
    dict[str, Any],
]


def normalize_text(value: Any) -> str:
    """Convert a value to a trimmed string."""

    if value is None:
        return ""

    return str(value).strip()


def require_resource_text(
    resource: dict[str, Any],
    field_name: str,
) -> str:
    """Read one required non-empty text field from a resource definition."""

    value = normalize_text(resource.get(field_name))

    if value == "":
        resource_name = normalize_text(resource.get("name")) or "Unknown resource"
        raise ValueError(
            f"{resource_name}: resource field {field_name!r} "
            "must be a non-empty string."
        )

    return value


def require_payload_builder(
    resource: dict[str, Any],
    field_name: str,
) -> PayloadBuilder:
    """Read and validate one payload-builder function from a resource."""

    builder = resource.get(field_name)

    if not callable(builder):
        resource_name = normalize_text(resource.get("name")) or "Unknown resource"
        raise ValueError(
            f"{resource_name}: resource field {field_name!r} "
            "must be callable."
        )

    return builder


def normalize_item_name(
    item: dict[str, Any],
    resource: dict[str, Any],
) -> str:
    """Return a safe display name for one execution-plan item."""

    name = normalize_text(item.get("name"))

    if name:
        return name

    singular_name = normalize_text(resource.get("singular_name")) or "object"
    return f"Unknown {singular_name}"


def validate_plan(plan: dict[str, Any]) -> None:
    """Validate the top-level structure of an execution plan."""

    if not isinstance(plan, dict):
        raise ValueError("The execution plan must be a dictionary.")

    for operation in ("create", "update", "match"):
        if not isinstance(plan.get(operation, []), list):
            raise ValueError(
                f"Execution plan {operation!r} must be a list."
            )


def get_object_id(
    item: dict[str, Any],
    resource: dict[str, Any],
) -> int:
    """Read and validate the Grocy object ID for an update operation."""

    item_name = normalize_item_name(item, resource)
    id_field = require_resource_text(resource, "grocy_id_field")

    object_id = item.get("object_id")

    if object_id is None:
        object_id = item.get(id_field)

    if object_id is None:
        legacy_id_field = normalize_text(
            resource.get("legacy_plan_id_field")
        )

        if legacy_id_field:
            object_id = item.get(legacy_id_field)

    if object_id is None:
        raise ValueError(
            f"{item_name}: update plan item is missing object_id."
        )

    try:
        return int(object_id)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{item_name}: invalid object_id {object_id!r}."
        ) from error


def apply_create(
    resource: dict[str, Any],
    item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> Any:
    """Create one Grocy object described by an execution-plan item."""

    endpoint = require_resource_text(resource, "grocy_endpoint")
    builder = require_payload_builder(resource, "build_create_payload")
    payload = builder(item, lookups)

    if not isinstance(payload, dict) or not payload:
        item_name = normalize_item_name(item, resource)
        raise ValueError(
            f"{item_name}: create payload must be a non-empty dictionary."
        )

    return post(endpoint, payload)


def apply_update(
    resource: dict[str, Any],
    item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> Any:
    """Update one existing Grocy object described by a plan item."""

    endpoint = require_resource_text(resource, "grocy_endpoint").rstrip("/")
    object_id = get_object_id(item, resource)
    builder = require_payload_builder(resource, "build_update_payload")
    payload = builder(item, lookups)

    if not isinstance(payload, dict) or not payload:
        item_name = normalize_item_name(item, resource)
        raise ValueError(
            f"{item_name}: update payload must be a non-empty dictionary."
        )

    return put(f"{endpoint}/{object_id}", payload)


def apply_items(
    *,
    resource: dict[str, Any],
    operation: str,
    items: list[dict[str, Any]],
    lookups: dict[str, dict[Any, Any]],
) -> int:
    """Apply all items for one supported operation and return the count."""

    handlers = {
        "create": apply_create,
        "update": apply_update,
    }

    handler = handlers.get(operation)

    if handler is None:
        raise ValueError(f"Unsupported apply operation {operation!r}.")

    completed = 0

    for item in items:
        if not isinstance(item, dict):
            raise ValueError(
                f"Every {operation} plan item must be a dictionary."
            )

        item_name = normalize_item_name(item, resource)
        print(f"{operation_symbol(operation)} {operation.upper():9} {item_name}")

        try:
            handler(resource, item, lookups)
        except Exception as error:
            print(f"    FAILED: {error}")
            raise

        completed += 1
        print(f"    {operation.capitalize()}d successfully.")
        print()

    return completed


def operation_symbol(operation: str) -> str:
    """Return the terminal symbol used for one plan operation."""

    return {
        "create": "+",
        "update": "~",
    }.get(operation, "?")


def apply_plan(
    resource: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, int]:
    """
    Apply a synchronization plan for any registered resource.

    The resource definition drives endpoint selection, payload generation,
    display names, object-ID handling, and whether lookup tables are needed.
    Processing stops on the first failed API operation so partial failure is
    never reported as a successful synchronization.
    """

    if not isinstance(resource, dict):
        raise ValueError("The resource definition must be a dictionary.")

    validate_plan(plan)

    create_items = plan.get("create", [])
    update_items = plan.get("update", [])
    match_items = plan.get("match", [])

    plural_name = require_resource_text(resource, "plural_name")

    print()
    print("=" * 40)
    print(f"Applying {plural_name.title()} Plan")
    print("=" * 40)
    print()
    print(f"{len(create_items)} {plural_name} to create")
    print(f"{len(update_items)} {plural_name} to update")
    print()

    if not create_items and not update_items:
        return {
            "created": 0,
            "updated": 0,
            "matched": len(match_items),
        }

    lookups: dict[str, dict[Any, Any]] = {}

    if resource.get("requires_lookups", False):
        print("Loading lookup tables...")
        lookups = build_lookups()
        print("Lookup tables loaded.")
        print()

    created_count = apply_items(
        resource=resource,
        operation="create",
        items=create_items,
        lookups=lookups,
    )

    updated_count = apply_items(
        resource=resource,
        operation="update",
        items=update_items,
        lookups=lookups,
    )

    print("=" * 40)
    print("Apply Summary")
    print("=" * 40)
    print()
    print(f"Matched: {len(match_items)}")
    print(f"Created: {created_count}")
    print(f"Updated: {updated_count}")

    return {
        "created": created_count,
        "updated": updated_count,
        "matched": len(match_items),
    }
