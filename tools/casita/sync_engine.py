"""
Generic synchronization engine.

A resource definition supplies catalog and Grocy mapping details. The engine
loads both sides, compares matching objects, and returns a generic execution
plan. It contains no product-specific logic and never applies changes itself.
"""

import csv
from pathlib import Path
from typing import Any

from casita.grocy import get
from casita.lookups import build_lookups
from casita.plan import build_plan


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_ROOT = PROJECT_ROOT / "catalog"


def require_resource_text(
    resource: dict[str, Any],
    field_name: str,
) -> str:
    """Read one required non-empty string from a resource definition."""

    value = str(resource.get(field_name, "")).strip()

    if value == "":
        resource_name = str(resource.get("name", "Unknown resource")).strip()
        raise ValueError(
            f"{resource_name}: resource field {field_name!r} "
            "must be a non-empty string."
        )

    return value


def load_catalog(resource: dict[str, Any]) -> list[dict[str, str]]:
    """Load the CSV catalog configured for one resource."""

    catalog_file = require_resource_text(resource, "catalog_file")
    path = CATALOG_ROOT / catalog_file

    if not path.exists():
        raise FileNotFoundError(f"Catalog file was not found: {path}")

    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def load_grocy(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Load all Grocy objects configured for one resource."""

    endpoint = require_resource_text(resource, "grocy_endpoint")
    rows = get(endpoint)

    if not isinstance(rows, list):
        raise ValueError(
            f"Grocy endpoint {endpoint!r} did not return a list."
        )

    return rows


def normalize_name(value: Any) -> str:
    """Normalize an object name for case-insensitive matching."""

    return str(value or "").strip().casefold()


def build_name_index(
    rows: list[dict[str, Any]],
    name_field: str,
) -> dict[str, dict[str, Any]]:
    """Build a case-insensitive object index and reject duplicate names."""

    index: dict[str, dict[str, Any]] = {}

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every Grocy object must be a dictionary.")

        name = normalize_name(row.get(name_field))

        if name == "":
            raise ValueError(
                f"A Grocy object is missing name field {name_field!r}."
            )

        if name in index:
            raise ValueError(
                f"Grocy contains duplicate names for {row.get(name_field)!r}."
            )

        index[name] = row

    return index


def build_resource_plan(
    resource: dict[str, Any],
    catalog: list[dict[str, Any]],
    grocy: list[dict[str, Any]],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build an execution plan from already-loaded resource data."""

    if not isinstance(resource, dict):
        raise ValueError("The resource definition must be a dictionary.")

    catalog_name_field = require_resource_text(
        resource,
        "catalog_name_field",
    )
    grocy_name_field = require_resource_text(
        resource,
        "grocy_name_field",
    )
    grocy_id_field = require_resource_text(
        resource,
        "grocy_id_field",
    )

    compare = resource.get("compare")

    if not callable(compare):
        raise ValueError("Resource field 'compare' must be callable.")

    plan = build_plan()
    grocy_by_name = build_name_index(grocy, grocy_name_field)
    seen_catalog_names: set[str] = set()

    for catalog_row in catalog:
        name = str(catalog_row.get(catalog_name_field, "")).strip()
        name_key = normalize_name(name)

        if name_key == "":
            raise ValueError(
                f"A catalog row is missing {catalog_name_field!r}."
            )

        if name_key in seen_catalog_names:
            raise ValueError(f"Catalog contains duplicate name {name!r}.")

        seen_catalog_names.add(name_key)
        grocy_row = grocy_by_name.get(name_key)

        if grocy_row is None:
            plan["create"].append(
                {
                    "name": name,
                    "catalog": catalog_row,
                }
            )
            continue

        object_id = grocy_row.get(grocy_id_field)

        if object_id is None:
            raise ValueError(
                f"Grocy object {name!r} is missing ID field "
                f"{grocy_id_field!r}."
            )

        differences = compare(catalog_row, grocy_row, lookups)

        plan_item = {
            "name": name,
            "object_id": object_id,
            "catalog": catalog_row,
            "grocy": grocy_row,
        }

        if differences:
            plan_item["changes"] = differences
            plan["update"].append(plan_item)
        else:
            plan["match"].append(plan_item)

    return plan


def sync_resource(resource: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Load, compare, and return the execution plan for one resource."""

    catalog = load_catalog(resource)
    grocy = load_grocy(resource)
    lookups: dict[str, dict[Any, Any]] = {}

    if resource.get("requires_lookups", False):
        lookups = build_lookups()

    return build_resource_plan(resource, catalog, grocy, lookups)
