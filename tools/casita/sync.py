"""User-facing synchronization workflow for registered resources."""

from typing import Any

from casita.apply import apply_plan
from casita.lookups import build_lookups
from casita.registry import (
    SYNC_ALL_COMMAND,
    get_resource,
    list_sync_resources,
)
from casita.sync_engine import (
    build_resource_plan,
    load_catalog,
    load_grocy,
)


def sync_registered_resource(
    resource_name: str,
    *,
    apply: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Synchronize any registered resource by name."""

    resource, plan = plan_registered_resource(resource_name)

    if apply:
        apply_plan(resource, plan)

    return plan


def plan_registered_resource(
    resource_name: str,
) -> tuple[
    dict[str, Any],
    dict[str, list[dict[str, Any]]],
]:
    """Build one native resource plan without presentation side effects."""

    resource = get_resource(resource_name)
    plural_name = resource["plural_name"]

    catalog_rows = load_catalog(resource)

    grocy_rows = load_grocy(resource)

    lookups: dict[str, dict[Any, Any]] = {}

    if resource.get("requires_lookups", False):
        lookups = build_lookups()

    plan = build_resource_plan(
        resource,
        catalog_rows,
        grocy_rows,
        lookups,
    )
    plan["_metadata"] = {
        "resource_label": plural_name,
        "catalog_count": len(catalog_rows),
        "backend_count": len(grocy_rows),
        "lookups_loaded": bool(resource.get("requires_lookups", False)),
    }

    return resource, plan


def sync_all(
    *,
    apply: bool = False,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Synchronize every registered orchestration resource in order."""

    plans: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for resource_name in list_sync_resources():
        plans[resource_name] = sync_registered_resource(
            resource_name,
            apply=apply,
        )

    return plans


def sync_command(
    command_name: str,
    *,
    apply: bool = False,
):
    """Route one CLI sync command to its synchronization workflow."""

    if command_name == SYNC_ALL_COMMAND:
        return sync_all(apply=apply)

    return sync_registered_resource(
        command_name,
        apply=apply,
    )


def sync_products(apply: bool = False):
    """Backward-compatible product synchronization command."""

    return sync_registered_resource("products", apply=apply)
