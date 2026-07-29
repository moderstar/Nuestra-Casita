"""
Recipe Position payload builders.

This module converts rows from catalog/recipe_positions.csv into payloads
accepted by the Grocy Recipe Positions API.
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
    default: int | float | None = None,
) -> int | float:
    """Convert a catalog value to a positive integer or decimal number."""

    text = normalize_text(value)

    if text == "" and default is not None:
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


def resolve_lookup_id(
    lookups: dict[str, dict[Any, Any]],
    lookup_name: str,
    value: Any,
    *,
    lookup_label: str,
    position_name: str,
) -> int:
    """Resolve one required Recipe Position relationship."""

    if lookup_name not in lookups:
        raise KeyError(
            f"{position_name}: lookup table {lookup_name!r} is missing."
        )

    return find_lookup_id(
        lookups[lookup_name],
        value,
        lookup_label=lookup_label,
        product_name=position_name,
    )


def recipe_position_name(catalog_position: dict[str, Any]) -> str:
    """Return the display name for one catalog Recipe Position."""

    recipe = normalize_text(catalog_position.get("Recipe"))
    product = normalize_text(catalog_position.get("Product"))

    return f"{recipe} / {product}"


def resolve_recipe_position_relationships(
    catalog_position: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> tuple[int, int, int]:
    """Resolve the Recipe, Product, and Quantity Unit IDs."""

    position_name = recipe_position_name(catalog_position)

    return (
        resolve_lookup_id(
            lookups,
            "recipes",
            catalog_position.get("Recipe"),
            lookup_label="Recipe",
            position_name=position_name,
        ),
        resolve_lookup_id(
            lookups,
            "products",
            catalog_position.get("Product"),
            lookup_label="Product",
            position_name=position_name,
        ),
        resolve_lookup_id(
            lookups,
            "units",
            catalog_position.get("Quantity Unit"),
            lookup_label="Quantity Unit",
            position_name=position_name,
        ),
    )


def build_recipe_position_create_payload(
    catalog_position: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a payload for creating a Grocy Recipe Position."""

    recipe = normalize_text(
        catalog_position.get("Recipe")
    )
    product = normalize_text(
        catalog_position.get("Product")
    )

    if recipe == "":
        raise ValueError(
            "Recipe Position Recipe field cannot be blank."
        )

    if product == "":
        raise ValueError(
            "Recipe Position Product field cannot be blank."
        )

    recipe_id, product_id, qu_id = (
        resolve_recipe_position_relationships(
            catalog_position,
            lookups,
        )
    )

    return {
        "recipe_id": recipe_id,
        "product_id": product_id,
        "amount": parse_positive_number(
            catalog_position.get("Amount"),
            field_name="Amount",
        ),
        "qu_id": qu_id,
        "only_check_single_unit_in_stock": parse_boolean(
            catalog_position.get("Only Check Single Unit"),
            field_name="Only Check Single Unit",
        ),
        "variable_amount": normalize_text(
            catalog_position.get("Variable Amount")
        ),
        "round_up": parse_boolean(
            catalog_position.get("Round Up"),
            field_name="Round Up",
        ),
        "not_check_stock_fulfillment": parse_boolean(
            catalog_position.get("Disable Stock Fulfillment"),
            field_name="Disable Stock Fulfillment",
        ),
        "ingredient_group": normalize_text(
            catalog_position.get("Ingredient Group")
        ),
        "note": normalize_text(
            catalog_position.get("Note")
        ),
        "price_factor": parse_positive_number(
            catalog_position.get("Price Factor"),
            field_name="Price Factor",
            default=1,
        ),
    }


def build_recipe_position_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a Recipe Position payload containing only changed fields."""

    name = normalize_text(
        plan_item.get("name")
    ) or "Unknown recipe position"
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
            f"{name}: no Recipe Position update fields were generated."
        )

    return payload
