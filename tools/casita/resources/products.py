"""
Products resource definition.

This module describes how catalog/products.csv maps to Grocy products and
adapts the product payload builders to the generic apply-engine interface.
It does not perform synchronization itself.
"""

from typing import Any

from casita.diff import compare_product
from casita.payloads import (
    build_product_create_payload,
    build_product_update_payload,
)


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a product creation payload from a generic create plan item."""

    product_name = str(
        plan_item.get("name", "Unknown product")
    ).strip() or "Unknown product"

    catalog_product = plan_item.get("catalog")

    if not isinstance(catalog_product, dict):
        raise ValueError(
            f"{product_name}: create plan item does not contain "
            "valid catalog data."
        )

    return build_product_create_payload(
        catalog_product,
        lookups,
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a product update payload from a generic update plan item."""

    del lookups
    return build_product_update_payload(plan_item)


PRODUCT_RESOURCE = {
    # Internal command and registry name.
    "name": "products",

    # Human-readable names used in terminal output.
    "singular_name": "product",
    "plural_name": "products",

    # Catalog configuration.
    "catalog_file": "products.csv",
    "catalog_name_field": "Product",

    # Grocy API configuration.
    "grocy_endpoint": "/objects/products",
    "grocy_name_field": "name",
    "grocy_id_field": "id",

    # Resource-specific functions exposed through one generic interface.
    "compare": compare_product,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,

    # Compatibility with plans created by the old product-specific engine.
    "legacy_plan_id_field": "product_id",

    # Products require Grocy lookup tables for comparison and creation.
    "requires_lookups": True,
}
