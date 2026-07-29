"""
Resource definitions for Nuestra Casita.

Each resource describes how one catalog type maps to Grocy.
"""

from casita.resources.locations import LOCATION_RESOURCE
from casita.resources.product_groups import PRODUCT_GROUP_RESOURCE
from casita.resources.quantity_units import QUANTITY_UNIT_RESOURCE
from casita.resources.products import PRODUCT_RESOURCE

__all__ = [
    "LOCATION_RESOURCE",
    "PRODUCT_GROUP_RESOURCE",
    "QUANTITY_UNIT_RESOURCE",
    "PRODUCT_RESOURCE",
]
