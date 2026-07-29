"""
Recipe Positions resource definition.

This module describes how catalog/recipe_positions.csv maps to native
Grocy 4.6 Recipe Positions and adapts its payload builders to the generic
apply-engine interface.
"""

from typing import Any, Callable

from casita.payloads import (
    build_recipe_position_create_payload,
    build_recipe_position_update_payload,
    parse_recipe_position_boolean,
    parse_recipe_position_positive_number,
    recipe_position_display_name,
    resolve_recipe_position_relationships,
)


def display_value(value: Any) -> str:
    """Convert a Recipe Position value into a clean display string."""

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


def catalog_identity(
    catalog_position: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build the stable Recipe/Product identity for a catalog position."""

    recipe_id, product_id, _ = resolve_recipe_position_relationships(
        catalog_position,
        lookups,
    )

    return f"{recipe_id}:{product_id}"


def grocy_identity(
    grocy_position: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build the stable Recipe/Product identity for a Grocy position."""

    del lookups
    recipe_id = grocy_position.get("recipe_id")
    product_id = grocy_position.get("product_id")

    if recipe_id is None or product_id is None:
        raise ValueError(
            "A Grocy Recipe Position is missing recipe_id or product_id."
        )

    return f"{recipe_id}:{product_id}"


def display_name(
    catalog_position: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return the Recipe/Product display name for a catalog position."""

    del lookups
    return recipe_position_display_name(catalog_position)


def compare_recipe_position(
    catalog_position: dict[str, Any],
    grocy_position: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Recipe Position with its Grocy object."""

    recipe_id, product_id, qu_id = (
        resolve_recipe_position_relationships(
            catalog_position,
            lookups,
        )
    )
    fields: tuple[
        tuple[str, str, Any, Callable[[Any], Any]],
        ...,
    ] = (
        ("Recipe", "recipe_id", recipe_id, normalize_number),
        ("Product", "product_id", product_id, normalize_number),
        (
            "Amount",
            "amount",
            parse_recipe_position_positive_number(
                catalog_position.get("Amount"),
                field_name="Amount",
            ),
            normalize_number,
        ),
        ("Quantity Unit", "qu_id", qu_id, normalize_number),
        (
            "Only Check Single Unit",
            "only_check_single_unit_in_stock",
            parse_recipe_position_boolean(
                catalog_position.get("Only Check Single Unit"),
                field_name="Only Check Single Unit",
            ),
            normalize_number,
        ),
        (
            "Variable Amount",
            "variable_amount",
            display_value(catalog_position.get("Variable Amount")),
            display_value,
        ),
        (
            "Round Up",
            "round_up",
            parse_recipe_position_boolean(
                catalog_position.get("Round Up"),
                field_name="Round Up",
            ),
            normalize_number,
        ),
        (
            "Disable Stock Fulfillment",
            "not_check_stock_fulfillment",
            parse_recipe_position_boolean(
                catalog_position.get("Disable Stock Fulfillment"),
                field_name="Disable Stock Fulfillment",
            ),
            normalize_number,
        ),
        (
            "Ingredient Group",
            "ingredient_group",
            display_value(catalog_position.get("Ingredient Group")),
            display_value,
        ),
        (
            "Note",
            "note",
            display_value(catalog_position.get("Note")),
            display_value,
        ),
        (
            "Price Factor",
            "price_factor",
            parse_recipe_position_positive_number(
                catalog_position.get("Price Factor"),
                field_name="Price Factor",
                default=1,
            ),
            normalize_number,
        ),
    )
    differences = []

    for label, api_field, catalog_value, normalize_grocy in fields:
        grocy_value = normalize_grocy(
            grocy_position.get(api_field)
        )

        if catalog_value != grocy_value:
            grocy_display = display_value(grocy_value)
            catalog_display = display_value(catalog_value)
            lookup_names = {
                "recipe_id": ("recipes_by_id", "Recipe"),
                "product_id": ("products_by_id", "Product"),
                "qu_id": ("units_by_id", "Quantity Unit"),
            }

            if api_field in lookup_names:
                lookup_name, catalog_key = lookup_names[api_field]
                grocy_display = display_value(
                    lookups.get(lookup_name, {}).get(grocy_value)
                )
                catalog_display = display_value(
                    catalog_position.get(catalog_key)
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
    """Build a Recipe Position create payload from a generic plan item."""

    name = str(
        plan_item.get("name") or "Unknown recipe position"
    ).strip()
    catalog_position = plan_item.get("catalog")

    if not isinstance(catalog_position, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_recipe_position_create_payload(
        catalog_position,
        lookups,
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Recipe Position update payload from a generic plan item."""

    del lookups
    return build_recipe_position_update_payload(plan_item)


RECIPE_POSITION_RESOURCE = {
    "name": "recipe-positions",
    "singular_name": "recipe position",
    "plural_name": "recipe positions",
    "catalog_file": "recipe_positions.csv",
    "grocy_endpoint": "/objects/recipes_pos",
    "grocy_id_field": "id",
    "catalog_identity": catalog_identity,
    "grocy_identity": grocy_identity,
    "display_name": display_name,
    "compare": compare_recipe_position,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": True,
}
