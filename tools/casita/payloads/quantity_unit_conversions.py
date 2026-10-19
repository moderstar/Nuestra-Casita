"""Payload and validation helpers for Grocy quantity-unit conversions."""

from decimal import Decimal, InvalidOperation
from typing import Any

from casita.payloads.products import find_lookup_id


def normalize_text(value: Any) -> str:
    """Convert a value to trimmed text."""

    if value is None:
        return ""

    return str(value).strip()


def parse_conversion_factor(value: Any) -> Decimal:
    """Return one finite, positive conversion factor without float loss."""

    text = normalize_text(value)

    try:
        factor = Decimal(text)
    except (InvalidOperation, ValueError) as error:
        raise ValueError(
            f"Factor must be a positive decimal, received {value!r}."
        ) from error

    if not factor.is_finite() or factor <= 0:
        raise ValueError(
            f"Factor must be greater than zero, received {value!r}."
        )

    return factor


def resolve_relationships(
    conversion: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> tuple[int, int, int | None]:
    """Resolve source unit, target unit, and optional Product references."""

    from_name = normalize_text(conversion.get("From Quantity Unit"))
    to_name = normalize_text(conversion.get("To Quantity Unit"))
    product_name = normalize_text(conversion.get("Product"))
    display_name = conversion_display_name(conversion)

    if from_name.casefold() == to_name.casefold() and from_name:
        raise ValueError(
            f"{display_name}: source and target Quantity Units must differ."
        )

    try:
        units = lookups["units"]
    except KeyError as error:
        raise KeyError("Quantity Unit lookup table 'units' is missing.") from error

    from_id = find_lookup_id(
        units,
        from_name,
        lookup_label="From Quantity Unit",
        product_name=display_name,
    )
    to_id = find_lookup_id(
        units,
        to_name,
        lookup_label="To Quantity Unit",
        product_name=display_name,
    )
    product_id = None

    if product_name:
        try:
            products = lookups["products"]
        except KeyError as error:
            raise KeyError("Product lookup table 'products' is missing.") from error

        product_id = find_lookup_id(
            products,
            product_name,
            lookup_label="Product",
            product_name=display_name,
        )

    return from_id, to_id, product_id


def conversion_display_name(conversion: dict[str, Any]) -> str:
    """Return a directional, scope-aware conversion label."""

    source = normalize_text(conversion.get("From Quantity Unit")) or "?"
    target = normalize_text(conversion.get("To Quantity Unit")) or "?"
    product = normalize_text(conversion.get("Product"))
    scope = f"Product {product}" if product else "Global"
    return f"{scope}: {source} -> {target}"


def build_quantity_unit_conversion_create_payload(
    conversion: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a validated Grocy conversion payload."""

    from_id, to_id, product_id = resolve_relationships(
        conversion,
        lookups,
    )
    factor = parse_conversion_factor(conversion.get("Factor"))

    return {
        "from_qu_id": from_id,
        "to_qu_id": to_id,
        "factor": format(factor, "f"),
        "product_id": product_id,
    }


def build_quantity_unit_conversion_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Build a conversion update containing only validated changes."""

    name = normalize_text(plan_item.get("name")) or "Unknown conversion"
    changes = plan_item.get("changes")

    if not isinstance(changes, list):
        raise ValueError(f"{name}: update plan changes must be a list.")

    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{name}: every update change must be a dictionary."
            )

        if change.get("api_field") != "factor":
            raise ValueError(
                f"{name}: only the conversion factor can be updated."
            )

        payload["factor"] = format(
            parse_conversion_factor(change.get("catalog_value")),
            "f",
        )

    if not payload:
        raise ValueError(f"{name}: no conversion update was generated.")

    return payload
