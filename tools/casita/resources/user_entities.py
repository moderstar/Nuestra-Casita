"""Grocy User Entity definition synchronization resource."""

from typing import Any, Callable

from casita.payloads import (
    build_user_entity_create_payload,
    build_user_entity_update_payload,
    parse_user_entity_boolean,
    parse_user_entity_caption,
)


def display_value(value: Any) -> str:
    """Convert a User Entity value into clean display text."""

    if value is None:
        return ""

    return str(value).strip()


def compare_user_entity(
    catalog_user_entity: dict[str, Any],
    grocy_user_entity: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare mutable definition metadata, never records or fields."""

    del lookups
    fields: tuple[tuple[str, str, Any, Callable[[Any], Any]], ...] = (
        (
            "Caption",
            "caption",
            parse_user_entity_caption(catalog_user_entity.get("Caption")),
            display_value,
        ),
        (
            "Description",
            "description",
            display_value(catalog_user_entity.get("Description")),
            display_value,
        ),
        (
            "Show in Sidebar",
            "show_in_sidebar_menu",
            parse_user_entity_boolean(
                catalog_user_entity.get("Show in Sidebar"),
                field_name="Show in Sidebar",
            ),
            lambda value: parse_user_entity_boolean(
                value,
                field_name="Grocy Show in Sidebar",
            ),
        ),
        (
            "Icon CSS Class",
            "icon_css_class",
            display_value(catalog_user_entity.get("Icon CSS Class")),
            display_value,
        ),
    )
    differences = []

    for label, api_field, catalog_value, normalize_grocy in fields:
        grocy_value = normalize_grocy(grocy_user_entity.get(api_field))

        if catalog_value != grocy_value:
            differences.append({
                "label": label,
                "api_field": api_field,
                "grocy_display": display_value(grocy_value),
                "catalog_display": display_value(catalog_value),
                "grocy_value": grocy_value,
                "catalog_value": catalog_value,
            })

    return differences


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Adapt a User Entity create item to the generic apply interface."""

    del lookups
    catalog_user_entity = plan_item.get("catalog")

    if not isinstance(catalog_user_entity, dict):
        raise ValueError(
            "User Entity create plan item has no valid catalog row."
        )

    return build_user_entity_create_payload(catalog_user_entity)


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Adapt a safe User Entity update to the generic apply interface."""

    del lookups
    return build_user_entity_update_payload(plan_item)


USER_ENTITY_RESOURCE = {
    "name": "user-entities",
    "singular_name": "user entity",
    "plural_name": "user entities",
    "catalog_file": "user_entities.csv",
    "catalog_name_field": "Name",
    "grocy_endpoint": "/objects/userentities",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_user_entity,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": False,
}
