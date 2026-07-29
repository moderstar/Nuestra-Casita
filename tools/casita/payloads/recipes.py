"""
Recipe payload builders.

This module converts rows from catalog/recipes.csv into payloads accepted by
the Grocy Recipes API.
"""

from typing import Any

from casita.payloads.products import find_lookup_id


def normalize_text(value: Any) -> str:
    """Convert a value to a trimmed string."""

    if value is None:
        return ""

    return str(value).strip()


def parse_boolean(value: Any, *, field_name: str) -> int:
    """Convert a catalog boolean value to the integer expected by Grocy."""

    text = normalize_text(value).casefold()

    if text in ("", "0", "false", "no", "off"):
        return 0

    if text in ("1", "true", "yes", "on"):
        return 1

    raise ValueError(
        f"{field_name} must be 1 or 0, received {value!r}."
    )


def parse_positive_number(
    value: Any,
    *,
    field_name: str,
    default: int = 1,
) -> int | float:
    """Convert a catalog value to a positive integer or decimal number."""

    text = normalize_text(value)

    if text == "":
        return default

    try:
        number = float(text)
    except ValueError as error:
        raise ValueError(
            f"{field_name} must be a positive number, "
            f"received {value!r}."
        ) from error

    if number <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero, "
            f"received {value!r}."
        )

    if number.is_integer():
        return int(number)

    return number


def resolve_product_id(
    catalog_recipe: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
    *,
    recipe_name: str,
) -> int | None:
    """Resolve the optional Product produced by a Recipe."""

    product_name = normalize_text(
        catalog_recipe.get("Produces Product")
    )

    if product_name == "":
        return None

    if "products" not in lookups:
        raise KeyError(
            f"{recipe_name}: lookup table 'products' is missing."
        )

    return find_lookup_id(
        lookups["products"],
        product_name,
        lookup_label="Produces Product",
        product_name=recipe_name,
    )


def build_recipe_create_payload(
    catalog_recipe: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a payload for creating a normal Grocy Recipe."""

    name = normalize_text(
        catalog_recipe.get("Recipe")
    )

    if name == "":
        raise ValueError(
            "Recipe catalog field cannot be blank."
        )

    return {
        "name": name,
        "description": normalize_text(
            catalog_recipe.get("Description")
        ),
        "base_servings": parse_positive_number(
            catalog_recipe.get("Base Servings"),
            field_name="Base Servings",
        ),
        "not_check_shoppinglist": parse_boolean(
            catalog_recipe.get("Ignore Shopping List"),
            field_name="Ignore Shopping List",
        ),
        "product_id": resolve_product_id(
            catalog_recipe,
            lookups,
            recipe_name=name,
        ),
        "type": "normal",
    }


def build_recipe_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a Recipe payload containing only changed fields."""

    name = normalize_text(
        plan_item.get("name")
    ) or "Unknown recipe"
    changes = plan_item.get("changes")

    if not isinstance(changes, list):
        raise ValueError(
            f"{name}: update plan changes must be a list."
        )

    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{name}: every update change must be a dictionary."
            )

        api_field = normalize_text(
            change.get("api_field")
        )

        if api_field == "":
            raise ValueError(
                f"{name}: an update change is missing api_field."
            )

        if "catalog_value" not in change:
            raise ValueError(
                f"{name}: change for {api_field!r} "
                "is missing catalog_value."
            )

        payload[api_field] = change["catalog_value"]

    if not payload:
        raise ValueError(
            f"{name}: no Recipe update fields were generated."
        )

    return payload
