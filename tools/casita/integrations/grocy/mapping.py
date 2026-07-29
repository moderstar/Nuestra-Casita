"""Translate native Grocy records into Nuestra Casita domain models."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from casita.domain import (
    Chore,
    Inventory,
    InventoryItem,
    Recipe,
    RecipeIngredient,
    ShoppingItem,
    ShoppingList,
)


GrocyRow = Mapping[str, Any]


def domain_id(resource: str, external_id: Any) -> str:
    """Create a stable opaque domain identity for one Grocy object."""

    if external_id is None or str(external_id).strip() == "":
        raise ValueError(f"Grocy {resource} record is missing its id.")

    return str(
        uuid5(
            NAMESPACE_URL,
            f"nuestra-casita:grocy:{resource}:{external_id}",
        )
    )


def decimal_value(
    value: Any,
    *,
    default: Decimal | None = None,
) -> Decimal | None:
    """Convert a Grocy numeric value without binary floating-point loss."""

    if value is None or str(value).strip() == "":
        return default

    try:
        return Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(
            f"Grocy returned an invalid numeric value {value!r}."
        ) from error


def boolean_value(value: Any) -> bool:
    """Normalize Grocy's integer and textual boolean representations."""

    if isinstance(value, bool):
        return value

    return str(value or "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def datetime_value(
    value: Any,
    local_timezone: ZoneInfo,
) -> datetime | None:
    """Parse a Grocy local datetime and normalize it to UTC."""

    text = str(value or "").strip()

    if text == "":
        return None

    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=local_timezone)

    return parsed.astimezone(timezone.utc)


def date_value(value: Any) -> date | None:
    """Parse a Grocy date while excluding its no-expiration sentinel."""

    text = str(value or "").strip()

    if text == "":
        return None

    parsed = date.fromisoformat(text[:10])

    if parsed.year >= 2999:
        return None

    return parsed


def identity_key(value: Any) -> str:
    """Normalize a private Grocy relationship identifier."""

    return str(value).strip()


def rows_by_id(rows: Iterable[GrocyRow]) -> dict[str, GrocyRow]:
    """Index native rows by their private Grocy identifiers."""

    return {
        identity_key(row["id"]): row
        for row in rows
        if row.get("id") is not None
    }


def map_inventory(
    household_id: str,
    stock_rows: Iterable[GrocyRow],
    units: Mapping[str, GrocyRow],
    *,
    measured_at: datetime,
) -> Inventory:
    """Translate Grocy's current aggregated stock into inventory items."""

    items = []

    for stock in stock_rows:
        product = stock.get("product")

        if not isinstance(product, Mapping):
            raise ValueError(
                "Grocy current stock is missing its product record."
            )

        product_id = stock.get("product_id", product.get("id"))
        aggregated = boolean_value(stock.get("is_aggregated_amount"))
        amount_field = "amount_aggregated" if aggregated else "amount"
        quantity = decimal_value(
            stock.get(amount_field),
            default=Decimal("0"),
        )
        minimum = decimal_value(
            product.get("min_stock_amount"),
            default=Decimal("0"),
        )
        unit = units.get(
            identity_key(product.get("qu_id_stock")),
            {},
        )

        items.append(
            InventoryItem(
                id=domain_id("product", product_id),
                name=str(product.get("name") or "").strip(),
                quantity=quantity or Decimal("0"),
                unit=str(unit.get("name") or "").strip(),
                expires_on=date_value(stock.get("best_before_date")),
                low_stock=bool(
                    minimum
                    and minimum > 0
                    and quantity is not None
                    and quantity <= minimum
                ),
            )
        )

    return Inventory(
        household_id=household_id,
        items=tuple(sorted(items, key=lambda item: item.name.casefold())),
        measured_at=measured_at,
    )


def map_shopping_lists(
    household_id: str,
    list_rows: Iterable[GrocyRow],
    item_rows: Iterable[GrocyRow],
    products: Mapping[str, GrocyRow],
    units: Mapping[str, GrocyRow],
    local_timezone: ZoneInfo,
) -> tuple[ShoppingList, ...]:
    """Translate named Grocy shopping lists and their current items."""

    grouped_items: dict[str, list[ShoppingItem]] = defaultdict(list)
    item_timestamps: dict[str, list[datetime]] = defaultdict(list)

    for item in item_rows:
        list_id = identity_key(item.get("shopping_list_id", 1))
        product = products.get(identity_key(item.get("product_id")), {})
        note = str(item.get("note") or "").strip()
        name = str(product.get("name") or note or "Shopping item").strip()
        unit = units.get(identity_key(item.get("qu_id")), {})
        timestamp = datetime_value(
            item.get("row_created_timestamp"),
            local_timezone,
        )

        grouped_items[list_id].append(
            ShoppingItem(
                id=domain_id("shopping-item", item.get("id")),
                name=name,
                quantity=decimal_value(item.get("amount")),
                unit=str(unit.get("name") or "").strip(),
                checked=boolean_value(item.get("done")),
                note=note,
            )
        )

        if timestamp is not None:
            item_timestamps[list_id].append(timestamp)

    lists = []

    for shopping_list in list_rows:
        list_id = shopping_list.get("id")
        list_key = identity_key(list_id)
        timestamps = item_timestamps.get(list_key, [])
        list_timestamp = datetime_value(
            shopping_list.get("row_created_timestamp"),
            local_timezone,
        )

        if list_timestamp is not None:
            timestamps.append(list_timestamp)

        lists.append(
            ShoppingList(
                id=domain_id("shopping-list", list_id),
                household_id=household_id,
                name=str(shopping_list.get("name") or "").strip(),
                items=tuple(grouped_items.get(list_key, ())),
                updated_at=max(timestamps) if timestamps else None,
            )
        )

    return tuple(sorted(lists, key=lambda item: item.name.casefold()))


def map_recipes(
    household_id: str,
    recipe_rows: Iterable[GrocyRow],
    position_rows: Iterable[GrocyRow],
    products: Mapping[str, GrocyRow],
    units: Mapping[str, GrocyRow],
) -> tuple[Recipe, ...]:
    """Translate normal Grocy recipes and declarative ingredients."""

    ingredients: dict[str, list[RecipeIngredient]] = defaultdict(list)

    for position in position_rows:
        product = products.get(
            identity_key(position.get("product_id")),
            {},
        )
        unit = units.get(identity_key(position.get("qu_id")), {})

        if not unit and product:
            unit = units.get(
                identity_key(product.get("qu_id_stock")),
                {},
            )

        ingredients[identity_key(position.get("recipe_id"))].append(
            RecipeIngredient(
                name=str(product.get("name") or "").strip(),
                quantity=decimal_value(position.get("amount")),
                unit=str(unit.get("name") or "").strip(),
                note=str(position.get("note") or "").strip(),
            )
        )

    recipes = []

    for recipe in recipe_rows:
        if str(recipe.get("type") or "normal").strip() != "normal":
            continue

        recipe_id = recipe.get("id")
        recipes.append(
            Recipe(
                id=domain_id("recipe", recipe_id),
                household_id=household_id,
                name=str(recipe.get("name") or "").strip(),
                description=str(recipe.get("description") or "").strip(),
                servings=decimal_value(
                    recipe.get("base_servings"),
                    default=Decimal("1"),
                ) or Decimal("1"),
                ingredients=tuple(
                    ingredients.get(identity_key(recipe_id), ())
                ),
            )
        )

    return tuple(sorted(recipes, key=lambda item: item.name.casefold()))


def map_chores(
    household_id: str,
    definition_rows: Iterable[GrocyRow],
    current_rows: Iterable[GrocyRow],
    local_timezone: ZoneInfo,
) -> tuple[Chore, ...]:
    """Translate Grocy chore definitions and current due state."""

    definitions = rows_by_id(definition_rows)
    chores = []

    for current in current_rows:
        chore_id = current.get("chore_id")
        definition = definitions.get(identity_key(chore_id), {})
        due_at = datetime_value(
            current.get("next_estimated_execution_time"),
            local_timezone,
        )

        if due_at is not None and due_at.year >= 2999:
            due_at = None

        assigned_user_id = current.get(
            "next_execution_assigned_to_user_id"
        )
        chores.append(
            Chore(
                id=domain_id("chore", chore_id),
                household_id=household_id,
                name=str(
                    definition.get("name")
                    or current.get("chore_name")
                    or ""
                ).strip(),
                description=str(
                    definition.get("description") or ""
                ).strip(),
                due_at=due_at,
                assigned_person_id=(
                    domain_id("person", assigned_user_id)
                    if assigned_user_id is not None
                    else None
                ),
                completed=False,
            )
        )

    return tuple(
        sorted(
            chores,
            key=lambda chore: (
                chore.due_at is None,
                chore.due_at or datetime.max.replace(tzinfo=timezone.utc),
                chore.name.casefold(),
            ),
        )
    )
