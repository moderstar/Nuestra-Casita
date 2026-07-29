"""
Generic execution engine for Nuestra Casita synchronization plans.

This module applies create and update operations for any registered resource.
Resource definitions provide the Grocy endpoint, object ID field, payload
builders, and lookup requirements. The engine contains no product-specific
logic.

Nothing in this module runs automatically. Changes are sent to Grocy only
when apply_plan() is called by an explicit --apply command.
"""

from typing import Any

from casita.grocy import post, put
from casita.lookups import build_lookups


def normalize_name(value: Any, resource: dict[str, Any]) -> str:
    """Return a clean display name for one plan item."""

    name = "" if value is None else str(value).strip()

    if name:
        return name

    singular_name = str(
        resource.get("singular_name", "object")
    ).strip() or "object"

    return f"Unknown {singular_name}"


def validate_resource(resource: dict[str, Any]) -> None:
    """Validate the fields required by the generic apply engine."""

    if not isinstance(resource, dict):
        raise ValueError(
            "The resource definition must be a dictionary."
        )

    required_fields = (
        "name",
        "singular_name",
        "plural_name",
        "grocy_endpoint",
        "grocy_id_field",
        "build_create_payload",
        "build_update_payload",
        "requires_lookups",
    )

    missing_fields = [
        field
        for field in required_fields
        if field not in resource
    ]

    if missing_fields:
        missing_text = ", ".join(missing_fields)
        raise ValueError(
            "Resource definition is missing required fields: "
            f"{missing_text}"
        )

    endpoint = str(resource["grocy_endpoint"]).strip()

    if not endpoint.startswith("/"):
        raise ValueError(
            "Resource grocy_endpoint must begin with '/'."
        )

    for builder_name in (
        "build_create_payload",
        "build_update_payload",
    ):
        if not callable(resource[builder_name]):
            raise ValueError(
                f"Resource {builder_name!r} must be callable."
            )


def validate_plan(plan: dict[str, Any]) -> None:
    """Validate the common execution-plan structure."""

    if not isinstance(plan, dict):
        raise ValueError(
            "The execution plan must be a dictionary."
        )

    for section_name in ("create", "update", "match"):
        section = plan.get(section_name, [])

        if not isinstance(section, list):
            raise ValueError(
                f"Execution plan {section_name!r} must be a list."
            )


def parse_object_id(
    item: dict[str, Any],
    resource: dict[str, Any],
) -> int:
    """Read and validate the Grocy object ID from a plan item."""

    display_name = normalize_name(
        item.get("name"),
        resource,
    )

    object_id = item.get("object_id")

    # Backward compatibility for plans produced before the generic engine.
    if object_id is None:
        legacy_id_field = str(
            resource.get("legacy_plan_id_field", "")
        ).strip()

        if legacy_id_field:
            object_id = item.get(legacy_id_field)

    if object_id is None:
        grocy_id_field = str(resource["grocy_id_field"])
        grocy_object = item.get("grocy")

        if isinstance(grocy_object, dict):
            object_id = grocy_object.get(grocy_id_field)

    if object_id is None:
        raise ValueError(
            f"{display_name}: update plan item is missing object_id."
        )

    try:
        return int(object_id)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{display_name}: invalid object_id {object_id!r}."
        ) from error


def apply_create(
    item: dict[str, Any],
    resource: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> Any:
    """Create one Grocy object described by a plan item."""

    display_name = normalize_name(
        item.get("name"),
        resource,
    )

    if not isinstance(item, dict):
        raise ValueError(
            "Every create plan item must be a dictionary."
        )

    payload_builder = resource["build_create_payload"]
    payload = payload_builder(item, lookups)

    if not isinstance(payload, dict) or not payload:
        raise ValueError(
            f"{display_name}: create payload must be a non-empty dictionary."
        )

    return post(
        resource["grocy_endpoint"],
        payload,
    )


def apply_update(
    item: dict[str, Any],
    resource: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> Any:
    """Update one existing Grocy object described by a plan item."""

    if not isinstance(item, dict):
        raise ValueError(
            "Every update plan item must be a dictionary."
        )

    display_name = normalize_name(
        item.get("name"),
        resource,
    )
    object_id = parse_object_id(item, resource)

    payload_builder = resource["build_update_payload"]
    payload = payload_builder(item, lookups)

    if not isinstance(payload, dict) or not payload:
        raise ValueError(
            f"{display_name}: update payload must be a non-empty dictionary."
        )

    endpoint = str(resource["grocy_endpoint"]).rstrip("/")

    return put(
        f"{endpoint}/{object_id}",
        payload,
    )


def apply_creates(
    create_items: list[dict[str, Any]],
    resource: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> int:
    """Apply all create operations and return the success count."""

    created_count = 0

    for item in create_items:
        display_name = normalize_name(
            item.get("name") if isinstance(item, dict) else None,
            resource,
        )

        print(f"+ CREATE    {display_name}")

        try:
            apply_create(item, resource, lookups)
        except Exception as error:
            print(f"    FAILED: {error}")
            raise

        created_count += 1
        print("    Created successfully.")
        print()

    return created_count


def apply_updates(
    update_items: list[dict[str, Any]],
    resource: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> int:
    """Apply all update operations and return the success count."""

    updated_count = 0

    for item in update_items:
        display_name = normalize_name(
            item.get("name") if isinstance(item, dict) else None,
            resource,
        )

        print(f"~ UPDATE    {display_name}")

        try:
            apply_update(item, resource, lookups)
        except Exception as error:
            print(f"    FAILED: {error}")
            raise

        updated_count += 1
        print("    Updated successfully.")
        print()

    return updated_count


def apply_plan(
    plan: dict[str, Any],
    resource: dict[str, Any],
) -> dict[str, int]:
    """
    Apply a complete synchronization plan for one registered resource.

    Matching objects require no action. Create and update payloads are built
    by the resource definition, then sent to the resource's Grocy endpoint.
    Processing stops immediately if any operation fails.
    """

    validate_resource(resource)
    validate_plan(plan)

    create_items = plan.get("create", [])
    update_items = plan.get("update", [])
    match_items = plan.get("match", [])

    singular_name = str(resource["singular_name"]).strip()
    plural_name = str(resource["plural_name"]).strip()

    print()
    print("=" * 40)
    print("Applying Plan")
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

    if resource["requires_lookups"]:
        print(f"Loading lookup tables for {singular_name} changes...")
        lookups = build_lookups()
        print("Lookup tables loaded.")
        print()

    created_count = apply_creates(
        create_items,
        resource,
        lookups,
    )

    updated_count = apply_updates(
        update_items,
        resource,
        lookups,
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
