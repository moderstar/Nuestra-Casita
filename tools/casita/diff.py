FIELDS = [
    {
        "label": "Minimum Stock",
        "catalog_key": "Minimum Stock",
        "api_field": "min_stock_amount",
        "name_to_id_lookup": None,
        "id_to_name_lookup": None,
        "value_type": "number",
    },
    {
        "label": "Product Group",
        "catalog_key": "Product Group",
        "api_field": "product_group_id",
        "name_to_id_lookup": "groups",
        "id_to_name_lookup": "groups_by_id",
        "value_type": "lookup",
    },
    {
        "label": "Default Location",
        "catalog_key": "Default Location",
        "api_field": "location_id",
        "name_to_id_lookup": "locations",
        "id_to_name_lookup": "locations_by_id",
        "value_type": "lookup",
    },
    {
        "label": "Stock Unit",
        "catalog_key": "Stock Unit",
        "api_field": "qu_id_stock",
        "name_to_id_lookup": "units",
        "id_to_name_lookup": "units_by_id",
        "value_type": "lookup",
    },
]


def normalize_number(value):
    """
    Convert a numeric value into an int or float.

    Empty values become None.
    """

    if value is None:
        return None

    text = str(value).strip()

    if text == "":
        return None

    number = float(text)

    if number.is_integer():
        return int(number)

    return number


def display_value(value):
    """
    Convert a raw value into a clean display string.
    """

    if value is None:
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip()


def lookup_id(lookup, name, label):
    """
    Resolve a catalog name to its Grocy object ID.

    Matching is exact first, then case-insensitive.
    """

    clean_name = str(name).strip()

    if clean_name in lookup:
        return lookup[clean_name]

    lowered_name = clean_name.lower()

    for lookup_name, object_id in lookup.items():
        if str(lookup_name).strip().lower() == lowered_name:
            return object_id

    raise ValueError(
        f'Unknown {label} "{clean_name}". '
        "Check the catalog value and Grocy lookup table."
    )


def compare_product(catalog_product, grocy_product, lookups):
    """
    Compare one catalog product against one Grocy product.

    Returns a list of self-contained change dictionaries.
    """

    differences = []

    for field in FIELDS:
        label = field["label"]
        catalog_key = field["catalog_key"]
        api_field = field["api_field"]
        value_type = field["value_type"]

        catalog_raw = catalog_product.get(catalog_key, "")
        grocy_raw = grocy_product.get(api_field)

        if value_type == "lookup":
            name_to_id = lookups[field["name_to_id_lookup"]]
            id_to_name = lookups[field["id_to_name_lookup"]]

            catalog_value = lookup_id(
                name_to_id,
                catalog_raw,
                label,
            )

            grocy_value = grocy_raw

            catalog_display = display_value(catalog_raw)
            grocy_display = display_value(
                id_to_name.get(grocy_value, "")
            )

            values_match = catalog_value == grocy_value

        elif value_type == "number":
            catalog_value = normalize_number(catalog_raw)
            grocy_value = normalize_number(grocy_raw)

            catalog_display = display_value(catalog_value)
            grocy_display = display_value(grocy_value)

            values_match = catalog_value == grocy_value

        else:
            catalog_value = str(catalog_raw).strip()
            grocy_value = display_value(grocy_raw)

            catalog_display = catalog_value
            grocy_display = grocy_value

            values_match = catalog_value == grocy_value

        if not values_match:
            differences.append(
                {
                    "label": label,
                    "api_field": api_field,
                    "grocy_display": grocy_display,
                    "catalog_display": catalog_display,
                    "grocy_value": grocy_value,
                    "catalog_value": catalog_value,
                }
            )

    return differences
