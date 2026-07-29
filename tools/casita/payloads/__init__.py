"""
Payload builders for Nuestra Casita.

Each module in this package converts catalog data into payloads accepted by
the Grocy REST API.
"""

from casita.payloads.products import (
    build_product_create_payload,
    build_product_update_payload,
    load_product_template,
)

from casita.payloads.product_groups import (
    build_product_group_create_payload,
    build_product_group_update_payload,
)

__all__ = [
    "build_product_create_payload",
    "build_product_update_payload",
    "load_product_template",
    "build_product_group_create_payload",
    "build_product_group_update_payload",
]
