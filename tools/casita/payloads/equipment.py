"""Payload builders for Grocy 4.6 Equipment definitions."""

from typing import Any


def normalize_text(value: Any) -> str:
    """Convert a catalog value into trimmed text."""

    if value is None:
        return ""

    return str(value).strip()


def parse_name(value: Any) -> str:
    """Validate the immutable Equipment synchronization identity."""

    name = normalize_text(value)

    if name == "":
        raise ValueError("Equipment catalog field cannot be blank.")

    return name


def build_equipment_create_payload(
    catalog_equipment: dict[str, Any],
) -> dict[str, Any]:
    """Build a payload containing only version-controlled fields."""

    return {
        "name": parse_name(catalog_equipment.get("Equipment")),
        "description": normalize_text(catalog_equipment.get("Description")),
    }


def build_equipment_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a safe update without touching manuals or Userfield values."""

    name = normalize_text(plan_item.get("name")) or "Unknown equipment"
    changes = plan_item.get("changes")

    if not isinstance(changes, list):
        raise ValueError(f"{name}: update plan changes must be a list.")

    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{name}: every update change must be a dictionary."
            )

        api_field = normalize_text(change.get("api_field"))

        if api_field != "description":
            raise ValueError(
                f"{name}: field {api_field!r} is not safely managed."
            )

        if "catalog_value" not in change:
            raise ValueError(
                f"{name}: change for {api_field!r} is missing catalog_value."
            )

        payload[api_field] = change["catalog_value"]

    if not payload:
        raise ValueError(f"{name}: no Equipment update fields were generated.")

    return payload
