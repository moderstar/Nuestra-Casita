"""
Chore payload builders.

This module converts rows from catalog/chores.csv into payloads accepted by
the Grocy Chores API.
"""

from datetime import datetime
from typing import Any

from casita.payloads.products import find_lookup_id


PERIOD_TYPES = {
    "adaptive",
    "daily",
    "hourly",
    "manually",
    "monthly",
    "weekly",
    "yearly",
}

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


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


def parse_active(value: Any) -> int:
    """Convert a catalog Active value to the integer expected by Grocy."""

    text = normalize_text(value).casefold()

    if text in ("", "1", "true", "yes", "active"):
        return 1

    if text in ("0", "false", "no", "inactive"):
        return 0

    raise ValueError(
        f"Active must be 1 or 0, received {value!r}."
    )


def parse_positive_integer(
    value: Any,
    *,
    field_name: str,
    default: int = 1,
) -> int:
    """Convert a catalog value to a positive integer."""

    text = normalize_text(value)

    if text == "":
        return default

    try:
        number = int(text)
    except ValueError as error:
        raise ValueError(
            f"{field_name} must be a positive integer, "
            f"received {value!r}."
        ) from error

    if number < 1:
        raise ValueError(
            f"{field_name} must be greater than zero, "
            f"received {value!r}."
        )

    return number


def parse_positive_number(
    value: Any,
    *,
    field_name: str,
) -> int | float:
    """Convert a catalog value to a positive integer or decimal number."""

    text = normalize_text(value)

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


def parse_period_type(value: Any) -> str:
    """Validate and return a native Grocy 4.6 Chore period type."""

    period_type = normalize_text(value).casefold()

    if period_type not in PERIOD_TYPES:
        choices = ", ".join(sorted(PERIOD_TYPES))
        raise ValueError(
            f"Period Type must be one of {choices}, "
            f"received {value!r}."
        )

    return period_type


def parse_period_config(value: Any, *, period_type: str) -> str:
    """Validate the weekly weekday list used by Grocy."""

    text = normalize_text(value).casefold()

    if period_type != "weekly":
        return ""

    selected_days = [
        part.strip()
        for part in text.split(",")
        if part.strip()
    ]

    if not selected_days:
        raise ValueError(
            "Period Config must contain at least one weekday "
            "for a weekly Chore."
        )

    invalid_days = [
        day
        for day in selected_days
        if day not in WEEKDAYS
    ]

    if invalid_days:
        invalid = ", ".join(invalid_days)
        raise ValueError(
            f"Period Config contains invalid weekdays: {invalid}."
        )

    return ",".join(
        day
        for day in WEEKDAYS
        if day in selected_days
    )


def parse_start_date(value: Any) -> str:
    """Validate the Grocy Chore schedule anchor timestamp."""

    text = normalize_text(value)

    if text == "":
        raise ValueError(
            "Start Date cannot be blank."
        )

    try:
        datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise ValueError(
            "Start Date must use YYYY-MM-DD HH:MM:SS format, "
            f"received {value!r}."
        ) from error

    return text


def build_chore_create_payload(
    catalog_chore: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a payload for creating a Grocy Chore."""

    name = normalize_text(
        catalog_chore.get("Chore")
    )

    if name == "":
        raise ValueError(
            "Chore catalog field cannot be blank."
        )

    period_type = parse_period_type(
        catalog_chore.get("Period Type")
    )
    period_interval = parse_positive_integer(
        catalog_chore.get("Period Interval"),
        field_name="Period Interval",
    )
    period_days = parse_positive_integer(
        catalog_chore.get("Period Days"),
        field_name="Period Days",
    )

    if period_type == "monthly" and period_days > 31:
        raise ValueError(
            f"{name}: Period Days cannot exceed 31 "
            "for a monthly Chore."
        )

    if period_type != "monthly":
        period_days = 1

    if period_type in ("adaptive", "manually"):
        period_interval = 1

    consume_product = parse_boolean(
        catalog_chore.get("Consume Product"),
        field_name="Consume Product",
    )
    product_id = None
    product_amount = None

    if consume_product:
        if "products" not in lookups:
            raise KeyError(
                f"{name}: lookup table 'products' is missing."
            )

        product_id = find_lookup_id(
            lookups["products"],
            catalog_chore.get("Product"),
            lookup_label="Product",
            product_name=name,
        )
        product_amount = parse_positive_number(
            catalog_chore.get("Product Amount"),
            field_name=f"{name}: Product Amount",
        )

    return {
        "name": name,
        "description": normalize_text(
            catalog_chore.get("Description")
        ),
        "period_type": period_type,
        "period_interval": period_interval,
        "period_days": period_days,
        "period_config": parse_period_config(
            catalog_chore.get("Period Config"),
            period_type=period_type,
        ),
        "start_date": parse_start_date(
            catalog_chore.get("Start Date")
        ),
        "track_date_only": parse_boolean(
            catalog_chore.get("Track Date Only"),
            field_name="Track Date Only",
        ),
        "rollover": parse_boolean(
            catalog_chore.get("Due Date Rollover"),
            field_name="Due Date Rollover",
        ),
        "consume_product_on_execution": consume_product,
        "product_id": product_id,
        "product_amount": product_amount,
        "assignment_type": "no-assignment",
        "assignment_config": "",
        "active": parse_active(
            catalog_chore.get("Active")
        ),
    }


def build_chore_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a Chore payload containing only changed fields."""

    name = normalize_text(
        plan_item.get("name")
    ) or "Unknown chore"
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
            f"{name}: no Chore update fields were generated."
        )

    return payload
