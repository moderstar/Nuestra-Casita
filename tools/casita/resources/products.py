"""
Products resource definition.

This module describes how catalog/products.csv maps to Grocy products.
It does not perform synchronization itself.
"""

from casita.diff import compare_product
from casita.payloads import (
    build_product_create_payload,
    build_product_update_payload,
)


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

    # Resource-specific functions.
    "compare": compare_product,
    "build_create_payload": build_product_create_payload,
    "build_update_payload": build_product_update_payload,

    # Products require Grocy lookup tables for comparisons and creation.
    "requires_lookups": True,
}
