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


def get_row_identity(
    resource: dict[str, Any],
    row: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
    *,
    source: str,
) -> str:
    """Return a normalized identity for one catalog or Grocy row."""

    identity_builder = resource.get(f"{source}_identity")

    if callable(identity_builder):
        identity = normalize_name(
            identity_builder(row, lookups)
        )
    else:
        field_name = require_resource_text(
            resource,
            f"{source}_name_field",
        )
        identity = normalize_name(row.get(field_name))

    if identity == "":
        raise ValueError(
            f"A {source} object has a blank synchronization identity."
        )

    return identity


def get_catalog_display_name(
    resource: dict[str, Any],
    catalog_row: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return the user-facing name for one catalog row."""

    display_name_builder = resource.get("display_name")

    if callable(display_name_builder):
        name = str(
            display_name_builder(catalog_row, lookups)
        ).strip()
    else:
        catalog_name_field = require_resource_text(
            resource,
            "catalog_name_field",
        )
        name = str(
            catalog_row.get(catalog_name_field, "")
        ).strip()

    if name == "":
        if not callable(display_name_builder):
            raise ValueError(
                f"A catalog row is missing {catalog_name_field!r}."
            )

        raise ValueError(
            "A catalog row has a blank display name."
        )

    return name


def build_identity_index(
    resource: dict[str, Any],
    rows: list[dict[str, Any]],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, dict[str, Any]]:
    """Index Grocy objects by the resource-defined identity."""

    if not callable(resource.get("grocy_identity")):
        grocy_name_field = require_resource_text(
            resource,
            "grocy_name_field",
        )
        return build_name_index(rows, grocy_name_field)

    index: dict[str, dict[str, Any]] = {}

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every Grocy object must be a dictionary.")

        identity = get_row_identity(
            resource,
            row,
            lookups,
            source="grocy",
        )

        if identity in index:
            raise ValueError(
                f"Grocy contains duplicate identity {identity!r}."
            )

        index[identity] = row

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

    grocy_id_field = require_resource_text(
        resource,
        "grocy_id_field",
    )

    compare = resource.get("compare")

    if not callable(compare):
        raise ValueError("Resource field 'compare' must be callable.")

    plan = build_plan()
    grocy_by_identity = build_identity_index(
        resource,
        grocy,
        lookups,
    )
    seen_catalog_identities: set[str] = set()

    for catalog_row in catalog:
        name = get_catalog_display_name(
            resource,
            catalog_row,
            lookups,
        )
        identity = get_row_identity(
            resource,
            catalog_row,
            lookups,
            source="catalog",
        )

        if identity in seen_catalog_identities:
            if not callable(resource.get("catalog_identity")):
                raise ValueError(
                    f"Catalog contains duplicate name {name!r}."
                )

            raise ValueError(
                f"Catalog contains duplicate identity {identity!r}."
            )

        seen_catalog_identities.add(identity)
        grocy_row = grocy_by_identity.get(identity)

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
