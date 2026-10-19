"""Payload builders for Grocy 4.6 User Entity definitions."""

import re
from typing import Any


NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def normalize_text(value: Any) -> str:
    """Convert a catalog value into trimmed text."""

    if value is None:
        return ""

    return str(value).strip()


def parse_name(value: Any) -> str:
    """Validate Grocy's immutable User Entity internal name."""

    name = normalize_text(value)

    if name == "":
        raise ValueError("User Entity Name cannot be blank.")

    if not NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "User Entity Name can contain only letters, numbers, and "
            f"underscores; received {value!r}."
        )

    return name


def parse_caption(value: Any) -> str:
    """Validate the required display caption."""

    caption = normalize_text(value)

    if caption == "":
        raise ValueError("User Entity Caption cannot be blank.")

    return caption


def parse_boolean(value: Any, *, field_name: str) -> int:
    """Parse a catalog boolean as Grocy's integer representation."""

    text = normalize_text(value).casefold()

    if text in ("", "1", "true", "yes", "on"):
        return 1

    if text in ("0", "false", "no", "off"):
        return 0

    raise ValueError(f"{field_name} must be 1 or 0, received {value!r}.")


def build_user_entity_create_payload(
    catalog_user_entity: dict[str, Any],
) -> dict[str, Any]:
    """Build a native User Entity definition payload."""

    return {
        "name": parse_name(catalog_user_entity.get("Name")),
        "caption": parse_caption(catalog_user_entity.get("Caption")),
        "description": normalize_text(
            catalog_user_entity.get("Description")
        ),
        "show_in_sidebar_menu": parse_boolean(
            catalog_user_entity.get("Show in Sidebar"),
            field_name="Show in Sidebar",
        ),
        "icon_css_class": normalize_text(
            catalog_user_entity.get("Icon CSS Class")
        ),
    }


def build_user_entity_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build an update limited to non-schema definition properties."""

    name = normalize_text(plan_item.get("name")) or "Unknown user entity"
    changes = plan_item.get("changes")

    if not isinstance(changes, list):
        raise ValueError(f"{name}: update plan changes must be a list.")

    safe_fields = {
        "caption",
        "description",
        "show_in_sidebar_menu",
        "icon_css_class",
    }
    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{name}: every update change must be a dictionary."
            )

        api_field = normalize_text(change.get("api_field"))

        if api_field not in safe_fields:
            raise ValueError(
                f"{name}: field {api_field!r} is not safely managed; "
                "User Entity names and schema identifiers are immutable."
            )

        if "catalog_value" not in change:
            raise ValueError(
                f"{name}: change for {api_field!r} is missing catalog_value."
            )

        payload[api_field] = change["catalog_value"]

    if not payload:
        raise ValueError(
            f"{name}: no User Entity update fields were generated."
        )

    return payload
