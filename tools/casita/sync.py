"""User-facing synchronization workflow for registered resources."""

from typing import Any

from casita.lookups import build_lookups
from casita.registry import get_resource
from casita.sync_engine import (
    build_resource_plan,
    load_catalog,
    load_grocy,
)


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
