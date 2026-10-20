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
from casita.payloads.equipment import (
    build_equipment_create_payload,
    build_equipment_update_payload,
)
from casita.payloads.locations import (
    build_location_create_payload,
    build_location_update_payload,
    parse_active as parse_location_active,
    parse_is_freezer as parse_location_is_freezer,
)
from casita.payloads.meal_plan import (
    build_meal_plan_create_payload,
    build_meal_plan_update_payload,
    entry_identity_from_values as meal_plan_entry_identity,
    parse_day as parse_meal_plan_day,
    parse_entry_type as parse_meal_plan_entry_type,
    resolve_entry as resolve_meal_plan_entry,
)
from casita.payloads.meal_plan_sections import (
    build_meal_plan_section_create_payload,
    build_meal_plan_section_update_payload,
    parse_sort_number as parse_meal_plan_section_sort_number,
    parse_time_info as parse_meal_plan_section_time,
)
from casita.payloads.product_groups import (
    build_product_group_create_payload,
    build_product_group_update_payload,
    parse_active as parse_product_group_active,
)
from casita.payloads.product_barcodes import (
    build_product_barcode_create_payload,
    build_product_barcode_update_payload,
    normalize_barcode as normalize_product_barcode,
    resolve_product_id as resolve_product_barcode_product_id,
)
from casita.payloads.quantity_units import (
    build_quantity_unit_create_payload,
    build_quantity_unit_update_payload,
    parse_active as parse_quantity_unit_active,
)
from casita.payloads.quantity_unit_conversions import (
    build_quantity_unit_conversion_create_payload,
    build_quantity_unit_conversion_update_payload,
    conversion_display_name,
    parse_conversion_factor,
    resolve_relationships as resolve_quantity_unit_conversion_relationships,
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
from casita.payloads.tasks import (
    build_task_create_payload,
    build_task_update_payload,
    parse_due_date as parse_task_due_date,
    resolve_category_id as resolve_task_category_id,
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
from casita.payloads.user_entities import (
    build_user_entity_create_payload,
    build_user_entity_update_payload,
    parse_boolean as parse_user_entity_boolean,
    parse_caption as parse_user_entity_caption,
    parse_name as parse_user_entity_name,
)

__all__ = [
    "build_battery_create_payload",
    "build_battery_update_payload",
    "build_equipment_create_payload",
    "build_equipment_update_payload",
    "build_location_create_payload",
    "build_location_update_payload",
    "build_meal_plan_create_payload",
    "build_meal_plan_update_payload",
    "build_meal_plan_section_create_payload",
    "build_meal_plan_section_update_payload",
    "build_product_group_create_payload",
    "build_product_group_update_payload",
    "build_product_barcode_create_payload",
    "build_product_barcode_update_payload",
    "build_quantity_unit_create_payload",
    "build_quantity_unit_update_payload",
    "build_quantity_unit_conversion_create_payload",
    "build_quantity_unit_conversion_update_payload",
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
    "build_task_create_payload",
    "build_task_update_payload",
    "build_user_entity_create_payload",
    "build_user_entity_update_payload",
    "build_userfield_create_payload",
    "build_userfield_update_payload",
    "load_product_template",
    "parse_battery_active",
    "parse_battery_charge_interval_days",
    "parse_location_active",
    "parse_location_is_freezer",
    "meal_plan_entry_identity",
    "parse_meal_plan_day",
    "parse_meal_plan_entry_type",
    "parse_meal_plan_section_sort_number",
    "parse_meal_plan_section_time",
    "resolve_meal_plan_entry",
    "parse_product_group_active",
    "normalize_product_barcode",
    "resolve_product_barcode_product_id",
    "parse_quantity_unit_active",
    "parse_conversion_factor",
    "conversion_display_name",
    "resolve_quantity_unit_conversion_relationships",
    "parse_recipe_boolean",
    "parse_recipe_positive_number",
    "parse_recipe_position_boolean",
    "parse_recipe_position_positive_number",
    "recipe_position_display_name",
    "resolve_recipe_position_relationships",
    "resolve_recipe_product_id",
    "parse_shopping_location_active",
    "parse_task_category_active",
    "parse_task_due_date",
    "resolve_task_category_id",
    "parse_userfield_boolean",
    "parse_userfield_caption",
    "parse_userfield_default_value",
    "parse_userfield_entity",
    "parse_userfield_name",
    "parse_userfield_sort_number",
    "parse_userfield_type",
    "userfield_display_name",
]
