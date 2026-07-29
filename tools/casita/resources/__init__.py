"""
Resource definitions for Nuestra Casita.

Each resource describes how one catalog type maps to Grocy.
"""

from casita.resources.product_groups import PRODUCT_GROUP_RESOURCE
from casita.resources.products import PRODUCT_RESOURCE

__all__ = [
    "PRODUCT_GROUP_RESOURCE",
    "PRODUCT_RESOURCE",
]
