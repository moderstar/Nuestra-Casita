"""
Nuestra Casita resource registry.

The registry provides one central location for discovering supported
catalog resources such as products, stores, chores, and recipes.
"""

from typing import Any

from casita.resources import (
    BATTERY_RESOURCE,
    CHORE_RESOURCE,
    LOCATION_RESOURCE,
    PRODUCT_GROUP_RESOURCE,
    PRODUCT_RESOURCE,
    QUANTITY_UNIT_RESOURCE,
    RECIPE_RESOURCE,
    RECIPE_POSITION_RESOURCE,
    SHOPPING_LOCATION_RESOURCE,
    TASK_CATEGORY_RESOURCE,
    USERFIELD_RESOURCE,
)


RESOURCES: dict[str, dict[str, Any]] = {
    BATTERY_RESOURCE["name"]: BATTERY_RESOURCE,
    CHORE_RESOURCE["name"]: CHORE_RESOURCE,
    LOCATION_RESOURCE["name"]: LOCATION_RESOURCE,
    PRODUCT_GROUP_RESOURCE["name"]: PRODUCT_GROUP_RESOURCE,
    PRODUCT_RESOURCE["name"]: PRODUCT_RESOURCE,
    QUANTITY_UNIT_RESOURCE["name"]: QUANTITY_UNIT_RESOURCE,
    RECIPE_RESOURCE["name"]: RECIPE_RESOURCE,
    RECIPE_POSITION_RESOURCE["name"]: RECIPE_POSITION_RESOURCE,
    SHOPPING_LOCATION_RESOURCE["name"]: SHOPPING_LOCATION_RESOURCE,
    TASK_CATEGORY_RESOURCE["name"]: TASK_CATEGORY_RESOURCE,
    USERFIELD_RESOURCE["name"]: USERFIELD_RESOURCE,
}

SYNC_ALL_COMMAND = "all"

SYNC_RESOURCE_ORDER = (
    "userfields",
    "product-groups",
    "quantity-units",
    "locations",
    "shopping-locations",
    "products",
    "task-categories",
    "chores",
    "batteries",
    "recipes",
    "recipe-positions",
)


def list_resources() -> list[str]:
    """
    Return the names of all registered resources.
    """

    return sorted(RESOURCES)


def list_sync_resources() -> list[str]:
    """
    Return registered resources in dependency-aware synchronization order.
    """

    missing_resources = [
        resource_name
        for resource_name in SYNC_RESOURCE_ORDER
        if resource_name not in RESOURCES
    ]

    if missing_resources:
        missing = ", ".join(missing_resources)
        raise ValueError(
            f"Sync order contains unregistered resources: {missing}"
        )

    return list(SYNC_RESOURCE_ORDER)


def list_sync_commands() -> list[str]:
    """
    Return every command accepted by the sync CLI.
    """

    return [
        SYNC_ALL_COMMAND,
        *list_resources(),
    ]


def get_resource(resource_name: str) -> dict[str, Any]:
    """
    Return one registered resource definition.

    Matching is case-insensitive and ignores surrounding whitespace.

    Raises:
        ValueError:
            If the requested resource name is blank or unregistered.
    """

    clean_name = str(resource_name).strip().casefold()

    if clean_name == "":
        raise ValueError(
            "Resource name cannot be blank."
        )

    resource = RESOURCES.get(clean_name)

    if resource is not None:
        return resource

    available = ", ".join(list_resources())

    raise ValueError(
        f"Unknown resource {resource_name!r}. "
        f"Available resources: {available or 'none'}"
    )


def register_resource(
    resource: dict[str, Any],
) -> None:
    """
    Register an additional resource definition.

    The resource must contain a non-empty 'name' field.

    Raises:
        ValueError:
            If the resource is invalid or its name is already registered.
    """

    if not isinstance(resource, dict):
        raise ValueError(
            "A resource definition must be a dictionary."
        )

    resource_name = str(
        resource.get("name", "")
    ).strip().casefold()

    if resource_name == "":
        raise ValueError(
            "A resource definition must contain a non-empty 'name'."
        )

    if resource_name in RESOURCES:
        raise ValueError(
            f"Resource {resource_name!r} is already registered."
        )

    RESOURCES[resource_name] = resource
