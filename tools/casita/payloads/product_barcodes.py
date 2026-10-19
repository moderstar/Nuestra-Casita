"""Payload and validation helpers for Grocy product barcodes."""

from typing import Any

from casita.payloads.products import find_lookup_id


def normalize_barcode(value: Any) -> str:
    """Return a required barcode string without numeric coercion."""

    if value is None:
        barcode = ""
    else:
        barcode = str(value).strip()

    if barcode == "":
        raise ValueError("Barcode must be a non-empty string.")

    return barcode


def resolve_product_id(
    barcode_definition: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> int:
    """Resolve the catalog Product name to its Grocy identifier."""

    barcode = normalize_barcode(barcode_definition.get("Barcode"))
    product_name = str(barcode_definition.get("Product") or "").strip()

    try:
        products = lookups["products"]
    except KeyError as error:
        raise KeyError("Product lookup table 'products' is missing.") from error

    return find_lookup_id(
        products,
        product_name,
        lookup_label="Product",
        product_name=f"Barcode {barcode}",
    )


def build_product_barcode_create_payload(
    barcode_definition: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a validated Grocy product-barcode association payload."""

    barcode = normalize_barcode(barcode_definition.get("Barcode"))
    product_id = resolve_product_id(barcode_definition, lookups)

    return {
        "product_id": product_id,
        "barcode": barcode,
    }


def build_product_barcode_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """Reject reassignment because barcode associations are immutable here."""

    name = str(plan_item.get("name") or "Unknown barcode").strip()
    raise ValueError(
        f"{name}: existing barcodes cannot be reassigned to another Product."
    )
