"""
Userfields resource definition.

This module describes how catalog/userfields.csv maps to native Grocy 4.6
Userfield definitions and adapts its payload builders to the generic
apply-engine interface.
"""

from typing import Any, Callable

from casita.payloads import (
    build_userfield_create_payload,
    build_userfield_update_payload,
    parse_userfield_boolean,
    parse_userfield_caption,
    parse_userfield_default_value,
    parse_userfield_entity,
    parse_userfield_name,
    parse_userfield_sort_number,
    parse_userfield_type,
    userfield_display_name,
)


def display_value(value: Any) -> str:
    """Convert a Userfield value into a clean display string."""

    if value is None:
        return ""

    return str(value).strip()


def normalize_number(value: Any) -> int | None:
    """Normalize a Grocy optional integer for comparison."""

    text = display_value(value)

    if text == "":
        return None

    return int(text)


def catalog_identity(
    catalog_userfield: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build the native Entity/Name identity for a catalog Userfield."""

    del lookups
    entity = parse_userfield_entity(
        catalog_userfield.get("Entity")
    )
    name = parse_userfield_name(
        catalog_userfield.get("Name")
    )

    return f"{entity}:{name}"


def grocy_identity(
    grocy_userfield: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build the native Entity/Name identity for a Grocy Userfield."""

    del lookups
    entity = parse_userfield_entity(
        grocy_userfield.get("entity")
    )
    name = parse_userfield_name(
        grocy_userfield.get("name")
    )

    return f"{entity}:{name}"


def display_name(
    catalog_userfield: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return the Entity/Name display name for a catalog Userfield."""

    del lookups
    return userfield_display_name(catalog_userfield)


def compare_userfield(
    catalog_userfield: dict[str, Any],
    grocy_userfield: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare one catalog Userfield with its Grocy definition."""

    del lookups
    field_type = parse_userfield_type(
        catalog_userfield.get("Type")
    )
    fields: tuple[
        tuple[str, str, Any, Callable[[Any], Any]],
        ...,
    ] = (
        (
            "Entity",
            "entity",
            parse_userfield_entity(catalog_userfield.get("Entity")),
            display_value,
        ),
        (
            "Name",
            "name",
            parse_userfield_name(catalog_userfield.get("Name")),
            display_value,
        ),
        (
            "Caption",
            "caption",
            parse_userfield_caption(catalog_userfield.get("Caption")),
            display_value,
        ),
        ("Type", "type", field_type, display_value),
        (
            "Configuration",
            "config",
            display_value(catalog_userfield.get("Configuration")),
            display_value,
        ),
        (
            "Sort Number",
            "sort_number",
            parse_userfield_sort_number(
                catalog_userfield.get("Sort Number")
            ),
            normalize_number,
        ),
        (
            "Show as Column",
            "show_as_column_in_tables",
            parse_userfield_boolean(
                catalog_userfield.get("Show as Column"),
                field_name="Show as Column",
            ),
            normalize_number,
        ),
        (
            "Mandatory",
            "input_required",
            parse_userfield_boolean(
                catalog_userfield.get("Mandatory"),
                field_name="Mandatory",
            ),
            normalize_number,
        ),
        (
            "Default Value",
            "default_value",
            parse_userfield_default_value(
                catalog_userfield.get("Default Value"),
                field_type=field_type,
            ),
            display_value,
        ),
    )
    differences = []

    for label, api_field, catalog_value, normalize_grocy in fields:
        grocy_value = normalize_grocy(
            grocy_userfield.get(api_field)
        )

        if catalog_value != grocy_value:
            differences.append(
                {
                    "label": label,
                    "api_field": api_field,
                    "grocy_display": display_value(grocy_value),
                    "catalog_display": display_value(catalog_value),
                    "grocy_value": grocy_value,
                    "catalog_value": catalog_value,
                }
            )

    return differences


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Userfield create payload from a generic plan item."""

    del lookups
    name = str(
        plan_item.get("name") or "Unknown userfield"
    ).strip()
    catalog_userfield = plan_item.get("catalog")

    if not isinstance(catalog_userfield, dict):
        raise ValueError(
            f"{name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_userfield_create_payload(
        catalog_userfield
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a Userfield update payload from a generic plan item."""

    del lookups
    return build_userfield_update_payload(plan_item)


USERFIELD_RESOURCE = {
    "name": "userfields",
    "singular_name": "userfield",
    "plural_name": "userfields",
    "catalog_file": "userfields.csv",
    "grocy_endpoint": "/objects/userfields",
    "grocy_id_field": "id",
    "catalog_identity": catalog_identity,
    "grocy_identity": grocy_identity,
    "display_name": display_name,
    "compare": compare_userfield,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
