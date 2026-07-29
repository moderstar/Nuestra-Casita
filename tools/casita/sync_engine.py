"""
Generic synchronization engine.

This module performs synchronization for any registered resource.

Resources describe:
    - catalog file
    - Grocy endpoint
    - comparison function
    - payload builders

The engine itself contains no product-specific logic.
"""

from pathlib import Path
import csv

from casita.grocy import get
from casita.lookups import build_lookups
from casita.plan import build_plan

CATALOG_ROOT = Path("/opt/Nuestra-Casita/catalog")


def load_catalog(resource):
    """
    Load one catalog CSV.
    """

    path = CATALOG_ROOT / resource["catalog_file"]

    with open(
        path,
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def load_grocy(resource):
    """
    Load all Grocy objects for one resource.
    """

    return get(resource["grocy_endpoint"])


def build_name_index(
    rows,
    name_field,
):
    """
    Build a case-insensitive lookup by name.
    """

    return {
        row[name_field].strip().lower(): row
        for row in rows
    }


def sync_resource(resource):
    """
    Synchronize one registered resource.

    Returns an execution plan.

    This engine does not print or apply anything.
    """

    catalog = load_catalog(resource)

    grocy = load_grocy(resource)

    lookups = {}

    if resource["requires_lookups"]:
        lookups = build_lookups()

    plan = build_plan()

    grocy_by_name = build_name_index(
        grocy,
        resource["grocy_name_field"],
    )

    compare = resource["compare"]

    catalog_name = resource["catalog_name_field"]

    for catalog_row in catalog:

        name = catalog_row[catalog_name].strip()

        grocy_row = grocy_by_name.get(
            name.lower()
        )

        if grocy_row is None:

            plan["create"].append(
                {
                    "name": name,
                    "catalog": catalog_row,
                }
            )

            continue

        differences = compare(
            catalog_row,
            grocy_row,
            lookups,
        )

        if differences:

            plan["update"].append(
                {
                    "name": name,
                    "product_id": grocy_row["id"],
                    "catalog": catalog_row,
                    "grocy": grocy_row,
                    "changes": differences,
                }
            )

        else:

            plan["match"].append(
                {
                    "name": name,
                    "product_id": grocy_row["id"],
                    "catalog": catalog_row,
                    "grocy": grocy_row,
                }
            )

    return plan
