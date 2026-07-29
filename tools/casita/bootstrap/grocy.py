"""Construct Nuestra Casita with the production Grocy integration."""

from dataclasses import replace

from casita.application import (
    DoctorService,
    MaintenanceService,
    SyncService,
)
from casita.bootstrap.application import (
    NuestraCasitaApplication,
    build_application,
)
from casita.bootstrap.configuration import (
    ApplicationConfiguration,
    load_configuration,
)
from casita.grocy import configure_client
from casita.exporter import export_products
from casita.lookups import show
from casita.integrations.grocy.client import GrocyApiClient
from casita.registry import (
    RESOURCES,
    get_resource,
    list_resources,
    list_sync_commands,
    list_sync_resources,
)
from casita.sync import sync_command
from casita.sync_engine import CATALOG_ROOT
from casita.validator import validate
from casita.dashboard import (
    DEFAULT_DASHBOARD_CONTRACT,
    DashboardContract,
)
from casita.integrations import Capability
from casita.integrations.grocy import GrocyReadAdapter


def build_grocy_application(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    timezone_name: str = "UTC",
    configuration: ApplicationConfiguration | None = None,
    dashboard_contract: DashboardContract = DEFAULT_DASHBOARD_CONTRACT,
) -> NuestraCasitaApplication:
    """Build an application whose household data is owned by Grocy."""

    config = configuration or load_configuration(
        strict=not (base_url and api_key),
    )

    if base_url or api_key:
        config = replace(
            config,
            grocy_url=base_url or config.grocy_url,
            grocy_api_key=api_key or config.grocy_api_key,
        )

    client = GrocyApiClient(
        config.grocy_url,
        config.grocy_api_key,
    )
    configure_client(client)
    grocy = GrocyReadAdapter(
        client,
        timezone_name=timezone_name,
        sync_runner=sync_command,
    )
    capabilities = (
        Capability.SHOPPING,
        Capability.INVENTORY,
        Capability.RECIPES,
        Capability.CHORES,
    )

    application = build_application(
        integrations=(grocy,),
        capability_owners={
            capability: (grocy.descriptor.key,)
            for capability in capabilities
        },
        dashboard_contract=dashboard_contract,
    )
    sync_service = SyncService(
        application.integrations,
        owner=grocy.descriptor.key,
        resources=tuple(list_sync_commands()),
    )
    doctor_service = DoctorService(
        application.integrations,
        configuration_exists=lambda: config.exists,
        catalog_root=CATALOG_ROOT,
        resources=RESOURCES,
        payload_registry_valid=_validate_payload_registry,
        resource_registry_valid=_validate_resource_registry,
    )
    maintenance_service = MaintenanceService(
        show_lookups=show,
        validate_catalog=validate,
        export_products=export_products,
    )

    return replace(
        application,
        sync=sync_service,
        doctor=doctor_service,
        maintenance=maintenance_service,
        configuration=config,
    )


def _validate_resource_registry() -> None:
    """Validate registered names and dependency-aware orchestration."""

    for name in list_resources():
        get_resource(name)

    list_sync_resources()


def _validate_payload_registry() -> None:
    """Validate the generic functions required by every resource."""

    for name in list_resources():
        resource = get_resource(name)

        for field in (
            "compare",
            "build_create_payload",
            "build_update_payload",
        ):
            if not callable(resource.get(field)):
                raise ValueError(
                    f"Resource {name!r} has invalid payload field {field!r}."
                )
