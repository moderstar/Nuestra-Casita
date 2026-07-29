"""
User-facing synchronization workflow.

This module handles terminal output and delegates plan creation and apply
behavior to the generic engines.
"""

from typing import Any

from casita.apply import apply_plan
from casita.registry import get_resource
from casita.sync_engine import sync_resource


def print_execution_plan(
    plan: dict[str, list[dict[str, Any]]],
) -> None:
    """Display a completed execution plan."""

    print("Execution Plan")
    print("=" * 40)
    print()

    for item in plan["update"]:
        print(f"~ UPDATE    {item['name']}")

        for change in item["changes"]:
            print(f"    {change['label']}")
            print(
                f"      Grocy:   "
                f"{change['grocy_display']}"
            )
            print(
                f"      Catalog: "
                f"{change['catalog_display']}"
            )

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


def sync(
    resource_name: str,
    *,
    apply: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Synchronize one registered resource by name."""

    resource = get_resource(resource_name)

    print(
        f"Building synchronization plan for "
        f"{resource['plural_name']}..."
    )
    print()

    plan = sync_resource(resource)

    print_execution_plan(plan)

    if apply:
        apply_plan(plan, resource)
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
        print(
            "    python tools/casita.py sync "
            f"{resource['name']} --apply"
        )

    return plan


def sync_products(
    apply: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Backward-compatible products synchronization command."""

    return sync("products", apply=apply)
