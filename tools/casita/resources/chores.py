"""
Chores resource definition.

This module describes how catalog/chores.csv maps to native Grocy 4.6 Chores
and adapts its payload builders to the generic apply-engine interface.
"""

from typing import Any, Callable

from casita.payloads import (
    build_chore_create_payload,
    build_chore_update_payload,
    parse_chore_active,
    parse_chore_boolean,
    parse_chore_period_config,
    parse_chore_period_type,
    parse_chore_positive_integer,
    parse_chore_positive_number,
    parse_chore_start_date,
)
from casita.payloads.products import find_lookup_id


def display_value(value: Any) -> str:
    """Convert a Chore value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def normalize_number(value: Any) -> int | float | None:
    """Normalize a Grocy optional number for comparison."""

    text = display_value(value)

    if text == "":
        return None

    number = float(text)

    if number.is_integer():
        return int(number)

    return number


def compare_chore(
    catalog_chore: dict[str, Any],
    grocy_chore: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Chore with its Grocy object."""

    name = display_value(
        catalog_chore.get("Chore")
    ) or "Unknown chore"
    period_type = parse_chore_period_type(
        catalog_chore.get("Period Type")
    )
    period_interval = parse_chore_positive_integer(
        catalog_chore.get("Period Interval"),
        field_name="Period Interval",
    )
    period_days = parse_chore_positive_integer(
        catalog_chore.get("Period Days"),
        field_name="Period Days",
    )

    if period_type == "monthly" and period_days > 31:
        raise ValueError(
            f"{name}: Period Days cannot exceed 31 "
            "for a monthly Chore."
        )

    if period_type != "monthly":
        period_days = 1

    if period_type in ("adaptive", "manually"):
        period_interval = 1

    parse_chore_start_date(
        catalog_chore.get("Start Date")
    )

    consume_product = parse_chore_boolean(
        catalog_chore.get("Consume Product"),
        field_name="Consume Product",
    )
    product_id = None
    product_amount = None

    if consume_product:
        if "products" not in lookups:
            raise KeyError(
                f"{name}: lookup table 'products' is missing."
            )

        product_id = find_lookup_id(
            lookups["products"],
            catalog_chore.get("Product"),
            lookup_label="Product",
            product_name=name,
        )
        product_amount = parse_chore_positive_number(
            catalog_chore.get("Product Amount"),
            field_name=f"{name}: Product Amount",
        )

    fields: tuple[
        tuple[str, str, Any, Callable[[Any], Any]],
        ...,
    ] = (
        (
            "Description",
            "description",
            display_value(catalog_chore.get("Description")),
            display_value,
        ),
        (
            "Period Type",
            "period_type",
            period_type,
            display_value,
        ),
        (
            "Period Interval",
            "period_interval",
            period_interval,
            normalize_number,
        ),
        (
            "Period Days",
            "period_days",
            period_days,
            normalize_number,
        ),
        (
            "Period Config",
            "period_config",
            parse_chore_period_config(
                catalog_chore.get("Period Config"),
                period_type=period_type,
            ),
            display_value,
        ),
        (
            "Track Date Only",
            "track_date_only",
            parse_chore_boolean(
                catalog_chore.get("Track Date Only"),
                field_name="Track Date Only",
            ),
            normalize_number,
        ),
        (
            "Due Date Rollover",
            "rollover",
            parse_chore_boolean(
                catalog_chore.get("Due Date Rollover"),
                field_name="Due Date Rollover",
            ),
            normalize_number,
        ),
        (
            "Consume Product",
            "consume_product_on_execution",
            consume_product,
            normalize_number,
        ),
        (
            "Product",
            "product_id",
            product_id,
            normalize_number,
        ),
        (
            "Product Amount",
            "product_amount",
            product_amount,
            normalize_number,
        ),
        (
            "Active",
            "active",
            parse_chore_active(
                catalog_chore.get("Active")
            ),
            normalize_number,
        ),
    )
    differences = []

    for label, api_field, catalog_value, normalize_grocy in fields:
        grocy_value = normalize_grocy(
            grocy_chore.get(api_field)
        )

        if catalog_value != grocy_value:
            grocy_display = display_value(grocy_value)
            catalog_display = display_value(catalog_value)

            if api_field == "product_id":
                grocy_display = display_value(
                    lookups.get("products_by_id", {}).get(grocy_value)
                )
                catalog_display = display_value(
                    catalog_chore.get("Product")
                )

            differences.append(
                {
                    "label": label,
                    "api_field": api_field,
                    "grocy_display": grocy_display,
                    "catalog_display": catalog_display,
                    "grocy_value": grocy_value,
                    "catalog_value": catalog_value,
                }
            )

    return differences


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Chore create payload from a generic plan item."""

    name = str(
        plan_item.get("name") or "Unknown chore"
    ).strip()
    catalog_chore = plan_item.get("catalog")

    if not isinstance(catalog_chore, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_chore_create_payload(
        catalog_chore,
        lookups,
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Chore update payload from a generic plan item."""

    del lookups
    return build_chore_update_payload(plan_item)


CHORE_RESOURCE = {
    "name": "chores",
    "singular_name": "chore",
    "plural_name": "chores",
    "catalog_file": "chores.csv",
    "catalog_name_field": "Chore",
    "grocy_endpoint": "/objects/chores",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_chore,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": True,
}
