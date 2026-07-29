"""User-facing synchronization workflow for registered resources."""

from typing import Any

from casita.apply import apply_plan
from casita.lookups import build_lookups
from casita.registry import get_resource
from casita.sync_engine import (
    build_resource_plan,
    load_catalog,
    load_grocy,
)


def print_execution_plan(
    resource: dict[str, Any],
    plan: dict[str, list[dict[str, Any]]],
) -> None:
    """Display a generic execution plan."""

    del resource

    print("Execution Plan")
    print("=" * 40)
    print()

    for item in plan["update"]:
        print(f"~ UPDATE    {item['name']}")

        for change in item.get("changes", []):
            label = change.get("label", change.get("api_field", "Field"))
            print(f"    {label}")
            print(f"      Grocy:   {change.get('grocy_display', '')}")
            print(f"      Catalog: {change.get('catalog_display', '')}")

        print()

    for item in plan["create"]:
        print(f"+ CREATE    {item['name']}")

    if plan["create"]:
        print()

    print("=" * 40)
    print("Summary")
    print("=" * 40)
    print(f"Match : {len(plan['match'])}")
    print(f"Update: {len(plan['update'])}")
    print(f"Create: {len(plan['create'])}")


def sync_registered_resource(
    resource_name: str,
    *,
    apply: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Synchronize any registered resource by name."""

    resource = get_resource(resource_name)
    plural_name = resource["plural_name"]

    print("Loading catalog...")
    catalog_rows = load_catalog(resource)
    print(f"Catalog {plural_name}: {len(catalog_rows)}")
    print()

    print("Loading Grocy...")
    grocy_rows = load_grocy(resource)
    print(f"Grocy {plural_name}: {len(grocy_rows)}")
    print()

    lookups: dict[str, dict[Any, Any]] = {}

    if resource.get("requires_lookups", False):
        print("Loading lookup tables...")
        lookups = build_lookups()
        print("Lookup tables loaded.")
        print()

    plan = build_resource_plan(
        resource,
        catalog_rows,
        grocy_rows,
        lookups,
    )
    print_execution_plan(resource, plan)

    if apply:
        apply_plan(resource, plan)
    else:
        print()
        print("=" * 40)
        print("Dry Run")
        print("=" * 40)
        print()
        print("No changes were made.")
        print()
        print("Run again with:")
        print()
        print(f"    python tools/casita.py sync {resource_name} --apply")

    return plan


def sync_products(apply: bool = False):
    """Backward-compatible product synchronization command."""

    return sync_registered_resource("products", apply=apply)
