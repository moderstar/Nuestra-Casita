"""
Product payload builders.

This module converts product rows from catalog/products.csv into payloads
that can be sent to the Grocy REST API.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_TEMPLATE_PATH = (
    PROJECT_ROOT
    / "catalog"
    / "templates"
    / "product.yaml"
)


def load_product_template() -> dict[str, Any]:
    """
    Load the default product creation template.

    Returns:
        A dictionary containing the default values for newly created
        Grocy products.

    Raises:
        FileNotFoundError:
            If catalog/templates/product.yaml does not exist.

        ValueError:
            If the YAML file is empty or does not contain a dictionary.
    """

    if not PRODUCT_TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            "Product template was not found:\n"
            f"    {PRODUCT_TEMPLATE_PATH}"
        )

    with PRODUCT_TEMPLATE_PATH.open(
        "r",
        encoding="utf-8",
    ) as template_file:
        template = yaml.safe_load(template_file)

    if template is None:
        raise ValueError(
            "The product template is empty:\n"
            f"    {PRODUCT_TEMPLATE_PATH}"
        )

    if not isinstance(template, dict):
        raise ValueError(
            "The product template must contain a YAML mapping:\n"
            f"    {PRODUCT_TEMPLATE_PATH}"
        )

    return template


def normalize_text(value: Any) -> str:
    """
    Convert a value to a trimmed string.

    None becomes an empty string.
    """

    if value is None:
        return ""

    return str(value).strip()


def parse_number(
    value: Any,
    *,
    default: int | float = 0,
) -> int | float:
    """
    Convert a catalog value into an integer or floating-point number.

    Examples:
        "2"   -> 2
        "2.5" -> 2.5
        ""    -> default

    Raises:
        ValueError:
            If a non-empty value cannot be converted to a number.
    """

    text = normalize_text(value)

    if text == "":
        return default

    try:
        number = float(text)
    except ValueError as error:
        raise ValueError(
            f"Expected a number but received {value!r}"
        ) from error

    if number.is_integer():
        return int(number)

    return number


def find_lookup_id(
    lookup: dict[Any, Any],
    name: Any,
    *,
    lookup_label: str,
    product_name: str,
) -> int:
    """
    Resolve a catalog name to a Grocy object ID.

    Lookup matching is case-insensitive and ignores surrounding spaces.

    Args:
        lookup:
            A dictionary mapping Grocy object names to IDs.

        name:
            The catalog value that needs to be resolved.

        lookup_label:
            Human-readable lookup type used in error messages.

        product_name:
            Product currently being processed.

    Returns:
        The matching Grocy object ID.

    Raises:
        ValueError:
            If the catalog value is blank or no matching lookup exists.
    """

    requested_name = normalize_text(name)

    if requested_name == "":
        raise ValueError(
            f"{product_name}: {lookup_label} cannot be blank."
        )

    requested_key = requested_name.casefold()

    for lookup_name, lookup_id in lookup.items():
        existing_key = normalize_text(lookup_name).casefold()

        if existing_key == requested_key:
            return int(lookup_id)

    available_names = sorted(
        normalize_text(lookup_name)
        for lookup_name in lookup
        if normalize_text(lookup_name)
    )

    available_text = ", ".join(available_names)

    raise ValueError(
        f"{product_name}: {lookup_label} "
        f"{requested_name!r} was not found in Grocy.\n"
        f"Available {lookup_label.lower()} values: "
        f"{available_text or 'none'}"
    )


def require_catalog_field(
    catalog_product: dict[str, Any],
    field_name: str,
    *,
    product_name: str,
) -> str:
    """
    Read a required field from a catalog product row.

    Raises:
        ValueError:
            If the field does not exist or contains a blank value.
    """

    if field_name not in catalog_product:
        raise ValueError(
            f"{product_name}: catalog column "
            f"{field_name!r} is missing."
        )

    value = normalize_text(catalog_product[field_name])

    if value == "":
        raise ValueError(
            f"{product_name}: catalog field "
            f"{field_name!r} cannot be blank."
        )

    return value


def build_product_create_payload(
    catalog_product: dict[str, Any],
    lookups: dict[str, dict[Any, Any]],
) -> dict[str, Any]:
    """
    Build the complete payload for creating a Grocy product.

    Values are assembled in this order:

        1. catalog/templates/product.yaml defaults
        2. catalog product values
        3. resolved Grocy lookup IDs

    The CSV columns currently supported are:

        Product
        Product Group
        Default Location
        Stock Unit
        Minimum Stock
        Notes

    Args:
        catalog_product:
            One row loaded from catalog/products.csv.

        lookups:
            Lookup dictionaries generated by casita.lookups.build_lookups().

    Returns:
        A dictionary ready to send to:

            POST /api/objects/products

    Raises:
        KeyError:
            If one of the required lookup dictionaries is missing.

        ValueError:
            If required catalog values are blank or cannot be resolved.
    """

    product_name = require_catalog_field(
        catalog_product,
        "Product",
        product_name="Unknown product",
    )

    required_lookup_names = (
        "groups",
        "locations",
        "units",
    )

    for lookup_name in required_lookup_names:
        if lookup_name not in lookups:
            raise KeyError(
                f"{product_name}: lookup table "
                f"{lookup_name!r} is missing."
            )

    product_group_name = require_catalog_field(
        catalog_product,
        "Product Group",
        product_name=product_name,
    )

    default_location_name = require_catalog_field(
        catalog_product,
        "Default Location",
        product_name=product_name,
    )

    stock_unit_name = require_catalog_field(
        catalog_product,
        "Stock Unit",
        product_name=product_name,
    )

    product_group_id = find_lookup_id(
        lookups["groups"],
        product_group_name,
        lookup_label="Product Group",
        product_name=product_name,
    )

    location_id = find_lookup_id(
        lookups["locations"],
        default_location_name,
        lookup_label="Default Location",
        product_name=product_name,
    )

    stock_unit_id = find_lookup_id(
        lookups["units"],
        stock_unit_name,
        lookup_label="Stock Unit",
        product_name=product_name,
    )

    minimum_stock = parse_number(
        catalog_product.get("Minimum Stock"),
        default=0,
    )

    notes = normalize_text(
        catalog_product.get("Notes")
    )

    payload = deepcopy(load_product_template())

    payload.update(
        {
            "name": product_name,
            "product_group_id": product_group_id,
            "location_id": location_id,
            "qu_id_stock": stock_unit_id,

            # Until the catalog has a separate purchase-unit column,
            # newly created products use the stock unit for purchases too.
            "qu_id_purchase": stock_unit_id,

            "min_stock_amount": minimum_stock,
            "description": notes,
        }
    )

    return payload


def build_product_update_payload(
    plan_item: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a payload for updating an existing Grocy product.

    Update plan changes are expected to contain:

        api_field
        catalog_value

    Only changed fields are included in the payload.

    Args:
        plan_item:
            One update item from the execution plan.

    Returns:
        A dictionary containing only fields that need to change.

    Raises:
        ValueError:
            If the plan item has no valid changes.
    """

    product_name = normalize_text(
        plan_item.get("name")
    ) or "Unknown product"

    changes = plan_item.get("changes")

    if not isinstance(changes, list):
        raise ValueError(
            f"{product_name}: update plan changes "
            "must be a list."
        )

    payload: dict[str, Any] = {}

    for change in changes:
        if not isinstance(change, dict):
            raise ValueError(
                f"{product_name}: every update change "
                "must be a dictionary."
            )

        api_field = normalize_text(
            change.get("api_field")
        )

        if api_field == "":
            raise ValueError(
                f"{product_name}: an update change "
                "is missing api_field."
            )

        if "catalog_value" not in change:
            raise ValueError(
                f"{product_name}: change for "
                f"{api_field!r} is missing catalog_value."
            )

        payload[api_field] = change["catalog_value"]

    if not payload:
        raise ValueError(
            f"{product_name}: no product update "
            "fields were generated."
        )

    return payload
