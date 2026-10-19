"""Payload and identity helpers for Grocy meal-plan entries."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

from casita.payloads.products import find_lookup_id


ENTRY_TYPES = {"note", "product", "recipe"}


def normalize_text(value: Any) -> str:
    """Convert a value to trimmed text."""

    if value is None:
        return ""

    return str(value).strip()


def parse_day(value: Any) -> str:
    """Validate a required date-only meal-plan day."""

    text = normalize_text(value)

    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(
            f"Day must use YYYY-MM-DD format, received {value!r}."
        ) from error

    return text


def parse_entry_type(value: Any) -> str:
    """Validate a native Grocy meal-plan entry type."""

    entry_type = normalize_text(value).casefold()

    if entry_type not in ENTRY_TYPES:
        choices = ", ".join(sorted(ENTRY_TYPES))
        raise ValueError(
            f"Entry Type must be one of {choices}, received {value!r}."
        )

    return entry_type


def parse_positive_decimal(
    value: Any,
    *,
    field_name: str,
    default: Decimal | None = None,
) -> Decimal:
    """Parse one finite positive amount without binary floating point."""

    text = normalize_text(value)

    if text == "" and default is not None:
        return default

    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError) as error:
        raise ValueError(
            f"{field_name} must be a positive decimal, received {value!r}."
        ) from error

    if not number.is_finite() or number <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero, received {value!r}."
        )

    return number


def resolve_lookup_id(
    lookups: dict[str, dict[Any, Any]],
    lookup_name: str,
    value: Any,
    *,
    label: str,
    entry_name: str,
) -> int:
    """Resolve one required meal-plan relationship."""

    if lookup_name not in lookups:
        raise KeyError(f"Meal Plan lookup table {lookup_name!r} is missing.")

    return find_lookup_id(
        lookups[lookup_name],
        value,
        lookup_label=label,
        product_name=entry_name,
    )


def reject_irrelevant_fields(
    entry: dict[str, Any],
    *,
    allowed: set[str],
    entry_name: str,
) -> None:
    """Reject type-specific values Grocy would not present for this type."""

    type_fields = {
        "Recipe",
        "Servings",
        "Product",
        "Amount",
        "Quantity Unit",
        "Note",
    }

    for field in sorted(type_fields - allowed):
        if normalize_text(entry.get(field)) != "":
            raise ValueError(
                f"{entry_name}: {field} is not supported for this Entry Type."
            )


def resolve_entry(
    entry: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Validate and resolve a catalog entry into native definition values."""

    day = parse_day(entry.get("Day"))
    entry_type = parse_entry_type(entry.get("Entry Type"))
    entry_name = f"{day} {entry_type}"
    section_id = resolve_lookup_id(
        lookups,
        "meal_plan_sections",
        entry.get("Meal Plan Section"),
        label="Meal Plan Section",
        entry_name=entry_name,
    )
    values: dict[str, Any] = {
        "day": day,
        "type": entry_type,
        "section_id": section_id,
    }

    if entry_type == "recipe":
        reject_irrelevant_fields(
            entry,
            allowed={"Recipe", "Servings"},
            entry_name=entry_name,
        )
        values["recipe_id"] = resolve_lookup_id(
            lookups,
            "recipes",
            entry.get("Recipe"),
            label="Recipe",
            entry_name=entry_name,
        )
        values["recipe_servings"] = parse_positive_decimal(
            entry.get("Servings"),
            field_name="Servings",
            default=Decimal("1"),
        )
    elif entry_type == "product":
        reject_irrelevant_fields(
            entry,
            allowed={"Product", "Amount", "Quantity Unit"},
            entry_name=entry_name,
        )
        values["product_id"] = resolve_lookup_id(
            lookups,
            "products",
            entry.get("Product"),
            label="Product",
            entry_name=entry_name,
        )
        values["product_amount"] = parse_positive_decimal(
            entry.get("Amount"),
            field_name="Amount",
        )
        values["product_qu_id"] = resolve_lookup_id(
            lookups,
            "units",
            entry.get("Quantity Unit"),
            label="Quantity Unit",
            entry_name=entry_name,
        )
    else:
        reject_irrelevant_fields(
            entry,
            allowed={"Note"},
            entry_name=entry_name,
        )
        note = normalize_text(entry.get("Note"))

        if note == "":
            raise ValueError(f"{entry_name}: Note cannot be blank.")

        values["note"] = note

    return values


def entry_identity_from_values(values: dict[str, Any]) -> str:
    """Build the conservative composite entry identity."""

    entry_type = values["type"]
    reference_fields = {
        "recipe": "recipe_id",
        "product": "product_id",
        "note": "note",
    }
    reference = values.get(reference_fields[entry_type])

    if reference is None or normalize_text(reference) == "":
        raise ValueError(
            f"Meal Plan {entry_type} entry is missing its identity reference."
        )

    if entry_type == "note":
        reference = sha256(str(reference).encode("utf-8")).hexdigest()

    return (
        f"{values['day']}:{values['section_id']}:"
        f"{entry_type}:{reference}"
    )


def build_meal_plan_create_payload(
    entry: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build an entry payload while excluding runtime completion state."""

    values = resolve_entry(entry, lookups)

    return {
        key: format(value, "f") if isinstance(value, Decimal) else value
        for key, value in values.items()
    }


def build_meal_plan_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build an update limited to safe type-specific amount fields."""

    name = normalize_text(plan_item.get("name")) or "Unknown meal plan entry"
    changes = plan_item.get("changes")
    managed_fields = {"recipe_servings", "product_amount", "product_qu_id"}

    if not isinstance(changes, list):
        raise ValueError(f"{name}: update plan changes must be a list.")

    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{name}: every update change must be a dictionary."
            )

        api_field = normalize_text(change.get("api_field"))

        if api_field not in managed_fields:
            raise ValueError(
                f"{name}: entry field {api_field!r} is not safely managed."
            )

        value = change.get("catalog_value")
        payload[api_field] = (
            format(value, "f") if isinstance(value, Decimal) else value
        )

    if not payload:
        raise ValueError(f"{name}: no Meal Plan update fields were generated.")

    return payload
