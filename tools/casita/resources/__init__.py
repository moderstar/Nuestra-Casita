"""
Resource definitions for Nuestra Casita.

Each resource describes how one catalog type maps to Grocy.
"""

from casita.resources.batteries import BATTERY_RESOURCE
from casita.resources.chores import CHORE_RESOURCE
from casita.resources.locations import LOCATION_RESOURCE
from casita.resources.product_groups import PRODUCT_GROUP_RESOURCE
from casita.resources.quantity_units import QUANTITY_UNIT_RESOURCE
from casita.resources.products import PRODUCT_RESOURCE
from casita.resources.recipes import RECIPE_RESOURCE
from casita.resources.recipe_positions import RECIPE_POSITION_RESOURCE
from casita.resources.shopping_locations import SHOPPING_LOCATION_RESOURCE
from casita.resources.task_categories import TASK_CATEGORY_RESOURCE

__all__ = [
    "BATTERY_RESOURCE",
    "CHORE_RESOURCE",
    "LOCATION_RESOURCE",
    "PRODUCT_GROUP_RESOURCE",
    "QUANTITY_UNIT_RESOURCE",
    "PRODUCT_RESOURCE",
    "RECIPE_RESOURCE",
    "RECIPE_POSITION_RESOURCE",
    "SHOPPING_LOCATION_RESOURCE",
    "TASK_CATEGORY_RESOURCE",
]
