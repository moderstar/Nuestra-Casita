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
from casita.payloads.recipes import (
    build_recipe_create_payload,
    build_recipe_update_payload,
    parse_boolean as parse_recipe_boolean,
    parse_positive_number as parse_recipe_positive_number,
    resolve_product_id as resolve_recipe_product_id,
)
from casita.payloads.recipe_positions import (
    build_recipe_position_create_payload,
    build_recipe_position_update_payload,
    parse_boolean as parse_recipe_position_boolean,
    parse_positive_number as parse_recipe_position_positive_number,
    recipe_position_name as recipe_position_display_name,
    resolve_recipe_position_relationships,
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
from casita.payloads.userfields import (
    build_userfield_create_payload,
    build_userfield_update_payload,
    parse_boolean as parse_userfield_boolean,
    parse_caption as parse_userfield_caption,
    parse_default_value as parse_userfield_default_value,
    parse_entity as parse_userfield_entity,
    parse_name as parse_userfield_name,
    parse_sort_number as parse_userfield_sort_number,
    parse_type as parse_userfield_type,
    userfield_name as userfield_display_name,
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
    "build_recipe_create_payload",
    "build_recipe_update_payload",
    "build_recipe_position_create_payload",
    "build_recipe_position_update_payload",
    "build_shopping_location_create_payload",
    "build_shopping_location_update_payload",
    "build_task_category_create_payload",
    "build_task_category_update_payload",
    "build_userfield_create_payload",
    "build_userfield_update_payload",
    "load_product_template",
    "parse_battery_active",
    "parse_battery_charge_interval_days",
    "parse_location_active",
    "parse_location_is_freezer",
    "parse_product_group_active",
    "parse_quantity_unit_active",
    "parse_recipe_boolean",
    "parse_recipe_positive_number",
    "parse_recipe_position_boolean",
    "parse_recipe_position_positive_number",
    "recipe_position_display_name",
    "resolve_recipe_position_relationships",
    "resolve_recipe_product_id",
    "parse_shopping_location_active",
    "parse_task_category_active",
    "parse_userfield_boolean",
    "parse_userfield_caption",
    "parse_userfield_default_value",
    "parse_userfield_entity",
    "parse_userfield_name",
    "parse_userfield_sort_number",
    "parse_userfield_type",
    "userfield_display_name",
    "parse_chore_active",
    "parse_chore_boolean",
    "parse_chore_period_config",
    "parse_chore_period_type",
    "parse_chore_positive_integer",
    "parse_chore_positive_number",
    "parse_chore_start_date",
]
