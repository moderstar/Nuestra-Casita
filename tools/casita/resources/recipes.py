"""
Recipes resource definition.

This module describes how catalog/recipes.csv maps to native Grocy 4.6 Recipe
definitions and adapts its payload builders to the generic apply-engine
interface.
"""

from typing import Any, Callable

from casita.payloads import (
    build_recipe_create_payload,
    build_recipe_update_payload,
    parse_recipe_boolean,
    parse_recipe_positive_number,
    resolve_recipe_product_id,
)


def display_value(value: Any) -> str:
    """Convert a Recipe value into a clean display string."""

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


def compare_recipe(
    catalog_recipe: dict[str, Any],
    grocy_recipe: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Recipe with its Grocy object."""

    name = display_value(
        catalog_recipe.get("Recipe")
    ) or "Unknown recipe"
    product_id = resolve_recipe_product_id(
        catalog_recipe,
        lookups,
        recipe_name=name,
    )
    fields: tuple[
        tuple[str, str, Any, Callable[[Any], Any]],
        ...,
    ] = (
        (
            "Description",
            "description",
            display_value(catalog_recipe.get("Description")),
            display_value,
        ),
        (
            "Base Servings",
            "base_servings",
            parse_recipe_positive_number(
                catalog_recipe.get("Base Servings"),
                field_name="Base Servings",
            ),
            normalize_number,
        ),
        (
            "Ignore Shopping List",
            "not_check_shoppinglist",
            parse_recipe_boolean(
                catalog_recipe.get("Ignore Shopping List"),
                field_name="Ignore Shopping List",
            ),
            normalize_number,
        ),
        (
            "Produces Product",
            "product_id",
            product_id,
            normalize_number,
        ),
    )
    differences = []

    for label, api_field, catalog_value, normalize_grocy in fields:
        grocy_value = normalize_grocy(
            grocy_recipe.get(api_field)
        )

        if catalog_value != grocy_value:
            grocy_display = display_value(grocy_value)
            catalog_display = display_value(catalog_value)

            if api_field == "product_id":
                grocy_display = display_value(
                    lookups.get("products_by_id", {}).get(grocy_value)
                )
                catalog_display = display_value(
                    catalog_recipe.get("Produces Product")
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
    """Build a Recipe create payload from a generic plan item."""

    name = str(
        plan_item.get("name") or "Unknown recipe"
    ).strip()
    catalog_recipe = plan_item.get("catalog")

    if not isinstance(catalog_recipe, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_recipe_create_payload(
        catalog_recipe,
        lookups,
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Recipe update payload from a generic plan item."""

    del lookups
    return build_recipe_update_payload(plan_item)


RECIPE_RESOURCE = {
    "name": "recipes",
    "singular_name": "recipe",
    "plural_name": "recipes",
    "catalog_file": "recipes.csv",
    "catalog_name_field": "Recipe",
    "grocy_endpoint": "/objects/recipes?query[]=type=normal",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_recipe,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": True,
}
