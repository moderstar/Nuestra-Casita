"""
Products resource definition.

This module describes how catalog/products.csv maps to Grocy products. It also
adapts the product payload functions to the common resource interface expected
by the generic apply engine.
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
    """Build a product-create payload from a generic plan item."""

    product_name = str(plan_item.get("name") or "Unknown product").strip()
    catalog_product = plan_item.get("catalog")

    if not isinstance(catalog_product, dict):
        raise ValueError(
            f"{product_name}: create plan item does not contain "
            "a valid catalog row."
        )

    return build_product_create_payload(catalog_product, lookups)


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a product-update payload from a generic plan item."""

    del lookups
    return build_product_update_payload(plan_item)


PRODUCT_RESOURCE = {
    "name": "products",
    "singular_name": "product",
    "plural_name": "products",
    "catalog_file": "products.csv",
    "catalog_name_field": "Product",
    "grocy_endpoint": "/objects/products",
    "grocy_name_field": "name",
    "grocy_id_field": "id",
    "compare": compare_product,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "legacy_plan_id_field": "product_id",
    "requires_lookups": True,
}
