"""Grocy quantity-unit conversion synchronization resource."""

from typing import Any

from casita.payloads import (
    build_quantity_unit_conversion_create_payload,
    build_quantity_unit_conversion_update_payload,
    conversion_display_name,
    parse_conversion_factor,
    resolve_quantity_unit_conversion_relationships,
)


def catalog_identity(
    conversion: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build the stable directional identity for a catalog conversion."""

    from_id, to_id, product_id = (
        resolve_quantity_unit_conversion_relationships(
            conversion,
            lookups,
        )
    )
    scope = f"product:{product_id}" if product_id is not None else "global"
    return f"{scope}:{from_id}:{to_id}"


def grocy_identity(
    conversion: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Build the stable directional identity for a Grocy conversion."""

    del lookups
    from_id = conversion.get("from_qu_id")
    to_id = conversion.get("to_qu_id")
    product_id = conversion.get("product_id")

    if from_id is None or to_id is None:
        raise ValueError(
            "A Grocy Quantity Unit Conversion is missing from_qu_id or "
            "to_qu_id."
        )

    scope = f"product:{product_id}" if product_id is not None else "global"
    return f"{scope}:{from_id}:{to_id}"


def display_name(
    conversion: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> str:
    """Return a scope-aware catalog display name."""

    del lookups
    return conversion_display_name(conversion)


def compare_conversion(
    catalog_conversion: dict[str, Any],
    grocy_conversion: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> list[dict[str, Any]]:
    """Compare the managed decimal factor for one conversion."""

    del lookups
    catalog_factor = parse_conversion_factor(
        catalog_conversion.get("Factor")
    )
    grocy_factor = parse_conversion_factor(
        grocy_conversion.get("factor")
    )

    if catalog_factor == grocy_factor:
        return []

    return [
        {
            "label": "Factor",
            "api_field": "factor",
            "grocy_display": format(grocy_factor, "f"),
            "catalog_display": format(catalog_factor, "f"),
            "grocy_value": grocy_factor,
            "catalog_value": catalog_factor,
        }
    ]


def build_create_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a conversion create payload from a generic plan item."""

    catalog_conversion = plan_item.get("catalog")

    if not isinstance(catalog_conversion, dict):
        raise ValueError(
            "Conversion create plan item has no valid catalog row."
        )

    return build_quantity_unit_conversion_create_payload(
        catalog_conversion,
        lookups,
    )


def build_update_payload(
    plan_item: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """Build a conversion update payload from a generic plan item."""

    del lookups
    return build_quantity_unit_conversion_update_payload(plan_item)


QUANTITY_UNIT_CONVERSION_RESOURCE = {
    "name": "quantity-unit-conversions",
    "singular_name": "quantity unit conversion",
    "plural_name": "quantity unit conversions",
    "catalog_file": "quantity_unit_conversions.csv",
    "grocy_endpoint": "/objects/quantity_unit_conversions",
    "grocy_id_field": "id",
    "catalog_identity": catalog_identity,
    "grocy_identity": grocy_identity,
    "display_name": display_name,
    "compare": compare_conversion,
    "build_create_payload": build_create_payload,
    "build_update_payload": build_update_payload,
    "requires_lookups": True,
}
