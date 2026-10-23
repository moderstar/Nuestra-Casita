"""Construct Nuestra Casita with the production Grocy integration."""

import os
from dataclasses import replace

from psycopg.conninfo import make_conninfo

from casita.persistence.entity_selections import EntitySelectionRepository

from casita.application import (
    CatalogApplicationService,
    IntegrationCatalogExecutor,
    IntegrationCatalogPlanner,
    DoctorService,
    MaintenanceService,
    SynchronizationApplicationService,
)
from casita.bootstrap.application import (
    NuestraCasitaApplication,
    build_application,
)
from casita.bootstrap.backends import (
    BackendRegistry,
    BackendResolver,
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
from casita.apply import apply_plan
from casita.sync import plan_registered_resource
from casita.sync_engine import CATALOG_ROOT
from casita.validator import validate
from casita.dashboard import (
    DEFAULT_DASHBOARD_CONTRACT,
    DashboardContract,
)
from casita.integrations import Capability
from casita.integrations.grocy import GrocyReadAdapter
from casita.integrations.home_assistant import (
    HomeAssistantApiClient,
    HomeAssistantReadAdapter,
)


class GrocyBackendProvider:
    """Provide Grocy integrations and catalog components to the bootstrap."""

    key = "grocy"

    def __init__(self, integration: GrocyReadAdapter) -> None:
        self._integration = integration

    @property
    def integrations(self):
        """Return the application-scoped Grocy integration."""

        return (self._integration,)

    @property
    def capability_owners(self):
        """Assign Grocy ownership of its declared household capabilities."""

        capabilities = (
            Capability.SHOPPING,
            Capability.INVENTORY,
            Capability.RECIPES,
            Capability.CHORES,
            Capability.MEAL_PLAN,
            Capability.TASKS,
        )
        integration_key = self._integration.descriptor.key
        return {
            capability: (integration_key,)
            for capability in capabilities
        }

    def catalog_planner(self, directory):
        """Build the integration-backed Grocy catalog planner."""

        return IntegrationCatalogPlanner(
            directory,
            owner=self._integration.descriptor.key,
        )

    def catalog_executor(self, directory):
        """Build the integration-backed Grocy catalog executor."""

        return IntegrationCatalogExecutor(
            directory,
            owner=self._integration.descriptor.key,
        )


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
        timeout=config.request_timeout_seconds,
    )
    configure_client(client)
    grocy = GrocyReadAdapter(
        client,
        timezone_name=timezone_name,
        sync_planner=plan_registered_resource,
        sync_applier=apply_plan,
    )
    provider = GrocyBackendProvider(grocy)
    registry = BackendRegistry()
    registry.register(provider)
    backend = BackendResolver(
        registry,
        default_key=GrocyBackendProvider.key,
    ).resolve()

    integrations = backend.integrations
    capability_owners = dict(backend.capability_owners)
    if config.home_assistant_configured:
        database_keys = (
            "CASITA_DATABASE_HOST",
            "CASITA_DATABASE_PORT",
            "CASITA_DATABASE_NAME",
            "CASITA_DATABASE_USER",
            "CASITA_DATABASE_PASSWORD",
        )
        database_values = [os.environ.get(key) for key in database_keys]

        entity_ids_provider = None

        if all(database_values):
            connection_string = make_conninfo(
                host=database_values[0],
                port=database_values[1],
                dbname=database_values[2],
                user=database_values[3],
                password=database_values[4],
            )
            repository = EntitySelectionRepository(connection_string)
            repository.initialize(
                config.household_id,
                config.home_assistant_entity_ids,
            )
            entity_ids_provider = repository.enabled_entity_ids

        home_assistant = HomeAssistantReadAdapter(
            HomeAssistantApiClient(
                config.home_assistant_url,
                config.home_assistant_token,
                timeout=config.request_timeout_seconds,
            ),
            entity_ids=config.home_assistant_entity_ids,
            entity_ids_provider=entity_ids_provider,
        )
        integrations = (*integrations, home_assistant)
        capability_owners[Capability.DEVICES] = (
            home_assistant.descriptor.key,
        )

    application = build_application(
        integrations=integrations,
        capability_owners=capability_owners,
        dashboard_contract=dashboard_contract,
    )
    catalog_service = CatalogApplicationService(
        backend.catalog_planner(application.integrations),
        backend.catalog_executor(application.integrations),
        resources=tuple(list_resources()),
    )
    sync_service = SynchronizationApplicationService(
        catalog_service,
        resource_order=tuple(list_sync_resources()),
        all_resource="all",
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
        catalog=catalog_service,
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
