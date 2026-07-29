"""
Generic synchronization engine.

This module builds an execution plan for any registered resource. Resource
definitions provide catalog, Grocy, comparison, and lookup configuration.
The engine contains no product-specific logic and does not print or apply
changes.
"""

import csv
from pathlib import Path
from typing import Any

from casita.grocy import get
from casita.lookups import build_lookups
from casita.plan import build_plan


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_ROOT = PROJECT_ROOT / "catalog"


def validate_resource(resource: dict[str, Any]) -> None:
    """Validate the fields required by the synchronization engine."""

    if not isinstance(resource, dict):
        raise ValueError(
            "The resource definition must be a dictionary."
        )

    required_fields = (
        "catalog_file",
        "catalog_name_field",
        "grocy_endpoint",
        "grocy_name_field",
        "grocy_id_field",
        "compare",
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

    if not callable(resource["compare"]):
        raise ValueError(
            "Resource 'compare' must be callable."
        )


def load_catalog(
    resource: dict[str, Any],
) -> list[dict[str, Any]]:
    """Load the resource's catalog CSV file."""

    path = CATALOG_ROOT / str(resource["catalog_file"])

    if not path.exists():
        raise FileNotFoundError(
            f"Catalog file was not found: {path}"
        )

    with path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def load_grocy(
    resource: dict[str, Any],
) -> list[dict[str, Any]]:
    """Load all Grocy objects for one resource."""

    objects = get(resource["grocy_endpoint"])

    if not isinstance(objects, list):
        raise ValueError(
            "Grocy resource response must be a list."
        )

    return objects


def normalize_index_name(value: Any) -> str:
    """Normalize a name used for case-insensitive matching."""

    if value is None:
        return ""

    return str(value).strip().casefold()


def build_name_index(
    rows: list[dict[str, Any]],
    name_field: str,
) -> dict[str, dict[str, Any]]:
    """Build a case-insensitive lookup by the configured name field."""

    index: dict[str, dict[str, Any]] = {}

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(
                "Every Grocy object must be a dictionary."
            )

        name = normalize_index_name(row.get(name_field))

        if name == "":
            continue

        if name in index:
            raise ValueError(
                f"Grocy contains duplicate names for field {name_field!r}: "
                f"{row.get(name_field)!r}"
            )

        index[name] = row

    return index


def sync_resource(
    resource: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Compare one catalog resource with Grocy and return an execution plan."""

    validate_resource(resource)

    catalog_rows = load_catalog(resource)
    grocy_rows = load_grocy(resource)

    lookups: dict[str, dict[Any, Any]] = {}

    if resource["requires_lookups"]:
        lookups = build_lookups()

    plan = build_plan()

    grocy_by_name = build_name_index(
        grocy_rows,
        str(resource["grocy_name_field"]),
    )

    compare = resource["compare"]
    catalog_name_field = str(resource["catalog_name_field"])
    grocy_id_field = str(resource["grocy_id_field"])

    for catalog_row in catalog_rows:
        if not isinstance(catalog_row, dict):
            raise ValueError(
                "Every catalog row must be a dictionary."
            )

        name = str(
            catalog_row.get(catalog_name_field, "")
        ).strip()

        if name == "":
            raise ValueError(
                f"Catalog field {catalog_name_field!r} cannot be blank."
            )

        grocy_row = grocy_by_name.get(
            normalize_index_name(name)
        )

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
                f"{name}: Grocy object is missing ID field "
                f"{grocy_id_field!r}."
            )

        differences = compare(
            catalog_row,
            grocy_row,
            lookups,
        )

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
