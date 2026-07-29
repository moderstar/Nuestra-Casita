"""
Payload builders for Nuestra Casita.

Each module in this package converts catalog data into payloads accepted by
the Grocy REST API.
"""

from casita.payloads.batteries import (
    build_battery_create_payload,
    build_battery_update_payload,
    parse_active as parse_battery_active,
    parse_charge_interval_days as parse_battery_charge_interval_days,
)
from casita.payloads.chores import (
    build_chore_create_payload,
    build_chore_update_payload,
    parse_active as parse_chore_active,
    parse_boolean as parse_chore_boolean,
    parse_period_config as parse_chore_period_config,
    parse_period_type as parse_chore_period_type,
    parse_positive_integer as parse_chore_positive_integer,
    parse_positive_number as parse_chore_positive_number,
    parse_start_date as parse_chore_start_date,
)
from casita.payloads.locations import (
    build_location_create_payload,
    build_location_update_payload,
    parse_active as parse_location_active,
    parse_is_freezer as parse_location_is_freezer,
)
from casita.payloads.product_groups import (
    build_product_group_create_payload,
    build_product_group_update_payload,
    parse_active as parse_product_group_active,
)
from casita.payloads.quantity_units import (
    build_quantity_unit_create_payload,
    build_quantity_unit_update_payload,
    parse_active as parse_quantity_unit_active,
)
from casita.payloads.products import (
    build_product_create_payload,
    build_product_update_payload,
    load_product_template,
)
from casita.payloads.shopping_locations import (
    build_shopping_location_create_payload,
    build_shopping_location_update_payload,
    parse_active as parse_shopping_location_active,
)
from casita.payloads.task_categories import (
    build_task_category_create_payload,
    build_task_category_update_payload,
    parse_active as parse_task_category_active,
)

__all__ = [
    "build_battery_create_payload",
    "build_battery_update_payload",
    "build_chore_create_payload",
    "build_chore_update_payload",
    "build_location_create_payload",
    "build_location_update_payload",
    "build_product_group_create_payload",
    "build_product_group_update_payload",
    "build_quantity_unit_create_payload",
    "build_quantity_unit_update_payload",
    "build_product_create_payload",
    "build_product_update_payload",
    "build_shopping_location_create_payload",
    "build_shopping_location_update_payload",
    "build_task_category_create_payload",
    "build_task_category_update_payload",
    "load_product_template",
    "parse_battery_active",
    "parse_battery_charge_interval_days",
    "parse_location_active",
    "parse_location_is_freezer",
    "parse_product_group_active",
    "parse_quantity_unit_active",
    "parse_shopping_location_active",
    "parse_task_category_active",
    "parse_chore_active",
    "parse_chore_boolean",
    "parse_chore_period_config",
    "parse_chore_period_type",
    "parse_chore_positive_integer",
    "parse_chore_positive_number",
    "parse_chore_start_date",
]
