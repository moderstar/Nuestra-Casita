"""Grocy Meal Plan Entries synchronization resource."""

from decimal import Decimal, InvalidOperation
from typing import Any

from casita.payloads import (
    build_meal_plan_create_payload,
    build_meal_plan_update_payload,
    meal_plan_entry_identity,
    parse_meal_plan_day,
    parse_meal_plan_entry_type,
    resolve_meal_plan_entry,
)


def display_value(value: Any) -> str:
    """Convert an entry value to display text."""

    if value is None:
        return ""

    return str(value).strip()


def normalize_id(value: Any, *, field_name: str) -> int:
    """Validate one required native relationship ID."""

    try:
        return int(display_value(value))
    except ValueError as error:
        raise ValueError(
            f"Grocy Meal Plan entry has invalid {field_name} {value!r}."
        ) from error


def normalize_decimal(value: Any, *, field_name: str) -> Decimal:
    """Normalize a finite positive native amount."""

    try:
        number = Decimal(display_value(value))
    except InvalidOperation as error:
        raise ValueError(
            f"Grocy Meal Plan entry has invalid {field_name} {value!r}."
        ) from error

    if not number.is_finite() or number <= 0:
        raise ValueError(
            f"Grocy Meal Plan entry has invalid {field_name} {value!r}."
        )

    return number


def catalog_identity(
    entry: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build a resolved composite identity for one catalog entry."""

    return meal_plan_entry_identity(resolve_meal_plan_entry(entry, lookups))


def grocy_identity(
    entry: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build and validate the composite identity for one Grocy entry."""

    del lookups
    entry_type = parse_meal_plan_entry_type(entry.get("type"))
    values = {
        "day": parse_meal_plan_day(entry.get("day")),
        "type": entry_type,
        "section_id": normalize_id(
            entry.get("section_id"),
            field_name="section_id",
        ),
    }
    reference_fields = {
        "recipe": "recipe_id",
        "product": "product_id",
        "note": "note",
    }
    reference_field = reference_fields[entry_type]

    if entry_type == "note":
        values[reference_field] = display_value(entry.get(reference_field))
    else:
        values[reference_field] = normalize_id(
            entry.get(reference_field),
            field_name=reference_field,
        )

    return meal_plan_entry_identity(values)


def display_name(
    entry: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return a human-readable catalog entry label."""

    values = resolve_meal_plan_entry(entry, lookups)
    entry_type = values["type"]
    reference = {
        "recipe": display_value(entry.get("Recipe")),
        "product": display_value(entry.get("Product")),
        "note": display_value(entry.get("Note")),
    }[entry_type]
    section = display_value(entry.get("Meal Plan Section"))
    return f"{values['day']} / {section} / {entry_type}: {reference}"


def compare_meal_plan_entry(
    catalog_entry: dict[str, Any],
    grocy_entry: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare only safe amount/unit fields within a stable identity."""

    values = resolve_meal_plan_entry(catalog_entry, lookups)
    entry_type = values["type"]
    fields = []

    if entry_type == "recipe":
        fields.append(
            (
                "Servings",
                "recipe_servings",
                values["recipe_servings"],
                normalize_decimal(
                    grocy_entry.get("recipe_servings"),
                    field_name="recipe_servings",
                ),
            )
        )
    elif entry_type == "product":
        fields.extend(
            (
                (
                    "Amount",
                    "product_amount",
                    values["product_amount"],
                    normalize_decimal(
                        grocy_entry.get("product_amount"),
                        field_name="product_amount",
                    ),
                ),
                (
                    "Quantity Unit",
                    "product_qu_id",
                    values["product_qu_id"],
                    normalize_id(
                        grocy_entry.get("product_qu_id"),
                        field_name="product_qu_id",
                    ),
                ),
            )
        )

    differences = []

    for label, api_field, catalog_value, grocy_value in fields:
        if catalog_value == grocy_value:
            continue

        grocy_display = display_value(grocy_value)
        catalog_display = display_value(catalog_value)

        if api_field == "product_qu_id":
            grocy_display = display_value(
                lookups.get("units_by_id", {}).get(grocy_value)
            )
            catalog_display = display_value(catalog_entry.get("Quantity Unit"))

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
    """Build a Meal Plan Entry create payload."""

    catalog_entry = plan_item.get("catalog")

    if not isinstance(catalog_entry, dict):
        raise ValueError("Meal Plan create item has no valid catalog row.")

    return build_meal_plan_create_payload(catalog_entry, lookups)


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a safe type-specific Meal Plan update payload."""

    del lookups
    return build_meal_plan_update_payload(plan_item)


MEAL_PLAN_RESOURCE = {
    "name": "meal-plan",
    "singular_name": "meal plan entry",
    "plural_name": "meal plan entries",
    "catalog_file": "meal_plan.csv",
    "grocy_endpoint": "/objects/meal_plan",
    "grocy_id_field": "id",
    "catalog_identity": catalog_identity,
    "grocy_identity": grocy_identity,
    "display_name": display_name,
    "compare": compare_meal_plan_entry,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": True,
}
