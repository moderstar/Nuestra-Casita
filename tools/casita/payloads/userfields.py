"""
Userfield payload builders.

This module converts rows from catalog/userfields.csv into payloads accepted
by the Grocy Userfields API.
"""

import re
from typing import Any


USERFIELD_TYPES = {
    "checkbox",
    "date",
    "datetime",
    "file",
    "image",
    "link",
    "link-with-title",
    "number-currency",
    "number-decimal",
    "number-integral",
    "preset-checklist",
    "preset-list",
    "text-multi-line",
    "text-single-line",
}

USERFIELD_ENTITIES = {
    "api_keys",
    "batteries",
    "battery_charge_cycles",
    "chores",
    "chores_log",
    "equipment",
    "locations",
    "meal_plan",
    "meal_plan_sections",
    "permission_hierarchy",
    "product_barcodes",
    "product_barcodes_view",
    "product_groups",
    "products",
    "products_average_price",
    "products_last_purchased",
    "quantity_unit_conversions",
    "quantity_unit_conversions_resolved",
    "quantity_units",
    "recipes",
    "recipes_nestings",
    "recipes_pos",
    "recipes_pos_resolved",
    "shopping_list",
    "shopping_lists",
    "shopping_locations",
    "stock",
    "stock_current_locations",
    "stock_log",
    "task_categories",
    "tasks",
    "userentities",
    "userfields",
    "userobjects",
    "users",
}

USERFIELD_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


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


def parse_entity(value: Any) -> str:
    """Validate a native Grocy 4.6 Userfield entity."""

    entity = normalize_text(value)

    if entity in USERFIELD_ENTITIES:
        return entity

    if entity.startswith("userentity-") and len(entity) > len("userentity-"):
        return entity

    choices = ", ".join(sorted(USERFIELD_ENTITIES))
    raise ValueError(
        "Entity must be a native Grocy 4.6 exposed entity, users, "
        f"or an existing userentity-<name>; received {value!r}. "
        f"Native entities: {choices}."
    )


def parse_name(value: Any) -> str:
    """Validate a Userfield's internal API name."""

    name = normalize_text(value)

    if name == "":
        raise ValueError(
            "Userfield Name cannot be blank."
        )

    if not USERFIELD_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "Userfield Name can contain only letters, numbers, "
            f"and underscores; received {value!r}."
        )

    return name


def parse_caption(value: Any) -> str:
    """Validate a Userfield's display caption."""

    caption = normalize_text(value)

    if caption == "":
        raise ValueError(
            "Userfield Caption cannot be blank."
        )

    return caption


def parse_type(value: Any) -> str:
    """Validate a native Grocy 4.6 Userfield type."""

    field_type = normalize_text(value).casefold()

    if field_type not in USERFIELD_TYPES:
        choices = ", ".join(sorted(USERFIELD_TYPES))
        raise ValueError(
            f"Type must be one of {choices}, received {value!r}."
        )

    return field_type


def parse_sort_number(value: Any) -> int | None:
    """Convert an optional sort number to a nonnegative integer."""

    text = normalize_text(value)

    if text == "":
        return None

    try:
        sort_number = int(text)
    except ValueError as error:
        raise ValueError(
            "Sort Number must be a nonnegative integer, "
            f"received {value!r}."
        ) from error

    if sort_number < 0:
        raise ValueError(
            "Sort Number cannot be negative, "
            f"received {value!r}."
        )

    return sort_number


def parse_default_value(value: Any, *, field_type: str) -> str:
    """Validate the native date/datetime default-value setting."""

    default_value = normalize_text(value).casefold()

    if field_type not in ("date", "datetime"):
        return ""

    if default_value not in ("", "now"):
        raise ValueError(
            "Default Value for date and datetime Userfields "
            f"must be blank or 'now', received {value!r}."
        )

    return default_value


def userfield_name(catalog_userfield: dict[str, Any]) -> str:
    """Return the display name for one catalog Userfield."""

    entity = normalize_text(catalog_userfield.get("Entity"))
    name = normalize_text(catalog_userfield.get("Name"))

    return f"{entity} / {name}"


def build_userfield_create_payload(
    catalog_userfield: dict[str, Any],
) -> dict[str, Any]:
    """Build a payload for creating a Grocy Userfield definition."""

    field_type = parse_type(
        catalog_userfield.get("Type")
    )

    return {
        "entity": parse_entity(
            catalog_userfield.get("Entity")
        ),
        "name": parse_name(
            catalog_userfield.get("Name")
        ),
        "caption": parse_caption(
            catalog_userfield.get("Caption")
        ),
        "type": field_type,
        "config": normalize_text(
            catalog_userfield.get("Configuration")
        ),
        "sort_number": parse_sort_number(
            catalog_userfield.get("Sort Number")
        ),
        "show_as_column_in_tables": parse_boolean(
            catalog_userfield.get("Show as Column"),
            field_name="Show as Column",
        ),
        "input_required": parse_boolean(
            catalog_userfield.get("Mandatory"),
            field_name="Mandatory",
        ),
        "default_value": parse_default_value(
            catalog_userfield.get("Default Value"),
            field_type=field_type,
        ),
    }


def build_userfield_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a Userfield payload containing only changed fields."""

    name = normalize_text(
        plan_item.get("name")
    ) or "Unknown userfield"
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
            f"{name}: no Userfield update fields were generated."
        )

    return payload
