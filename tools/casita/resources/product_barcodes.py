"""Grocy product-barcode synchronization resource."""

from typing import Any

from casita.payloads import (
    build_product_barcode_create_payload,
    build_product_barcode_update_payload,
    normalize_product_barcode,
    resolve_product_barcode_product_id,
)


def catalog_identity(
    barcode_definition: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return Grocy 4.6's case-insensitive barcode identity."""

    del lookups
    return normalize_product_barcode(barcode_definition.get("Barcode"))


def grocy_identity(
    barcode_definition: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return a validated native barcode identity."""

    del lookups
    return normalize_product_barcode(barcode_definition.get("barcode"))


def display_name(
    barcode_definition: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return the exact barcode value used in the catalog."""

    del lookups
    return normalize_product_barcode(barcode_definition.get("Barcode"))


def compare_barcode(
    catalog_barcode: dict[str, Any],
    grocy_barcode: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Match one association or reject an unsafe Product reassignment."""

    barcode = normalize_product_barcode(catalog_barcode.get("Barcode"))
    catalog_product_id = resolve_product_barcode_product_id(
        catalog_barcode,
        lookups,
    )
    grocy_product_id = grocy_barcode.get("product_id")

    if grocy_product_id is None:
        raise ValueError(
            f"Barcode {barcode}: Grocy record is missing product_id."
        )

    if str(grocy_product_id) != str(catalog_product_id):
        product_name = str(catalog_barcode.get("Product") or "").strip()
        raise ValueError(
            f"Barcode {barcode} is already assigned to a different Product; "
            f"refusing to reassign it to {product_name!r}."
        )

    return []


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a barcode create payload from a generic plan item."""

    catalog_barcode = plan_item.get("catalog")

    if not isinstance(catalog_barcode, dict):
        raise ValueError("Barcode create plan item has no valid catalog row.")

    return build_product_barcode_create_payload(catalog_barcode, lookups)


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Reject updates; compare_barcode prevents reassignment plans."""

    del lookups
    return build_product_barcode_update_payload(plan_item)


PRODUCT_BARCODE_RESOURCE = {
    "name": "product-barcodes",
    "singular_name": "product barcode",
    "plural_name": "product barcodes",
    "catalog_file": "product_barcodes.csv",
    "grocy_endpoint": "/objects/product_barcodes",
    "grocy_id_field": "id",
    "catalog_identity": catalog_identity,
    "grocy_identity": grocy_identity,
    "display_name": display_name,
    "compare": compare_barcode,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": True,
}
