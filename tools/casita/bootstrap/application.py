"""
Construct the Nuestra Casita application object graph.

This module is the composition root. It owns dependency injection and object
lifetime, but contains no household business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from casita.application import (
    BudgetService,
    CalendarService,
    ChoreService,
    DashboardService,
    DeviceService,
    IntegrationDirectory,
    InventoryService,
    MediaService,
    NotificationService,
    RecipeService,
    ShoppingService,
    SyncService,
)
from casita.bootstrap.configuration import ApplicationConfiguration
from casita.dashboard import (
    DEFAULT_DASHBOARD_CONTRACT,
    DashboardContract,
)
from casita.integrations import Capability, Integration


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Hold the household capability services for one application lifetime."""

    shopping: ShoppingService
    inventory: InventoryService
    recipes: RecipeService
    chores: ChoreService
    calendar: CalendarService
    budget: BudgetService
    notifications: NotificationService
    devices: DeviceService
    media: MediaService


@dataclass(frozen=True, slots=True)
class NuestraCasitaApplication:
    """Expose the fully assembled backend-neutral application."""

    integrations: IntegrationDirectory
    services: ApplicationServices
    dashboard: DashboardService
    sync: SyncService | None = None
    doctor: DoctorService | None = None
    configuration: ApplicationConfiguration | None = None


def build_application(
    *,
    integrations: Iterable[Integration] = (),
    capability_owners: (
        Mapping[Capability, tuple[str, ...]] | None
    ) = None,
    dashboard_contract: DashboardContract = DEFAULT_DASHBOARD_CONTRACT,
) -> NuestraCasitaApplication:
    """
    Construct one complete Nuestra Casita application object graph.

    Concrete adapter instances are registered explicitly by the process entry
    point. The returned object owns their application-scoped directory,
    services, and dashboard assembler.
    """

    directory = IntegrationDirectory(
        integrations,
        owners=capability_owners,
    )
    services = ApplicationServices(
        shopping=ShoppingService(directory),
        inventory=InventoryService(directory),
        recipes=RecipeService(directory),
        chores=ChoreService(directory),
        calendar=CalendarService(directory),
        budget=BudgetService(directory),
        notifications=NotificationService(directory),
        devices=DeviceService(directory),
        media=MediaService(directory),
    )
    dashboard = DashboardService(
        shopping=services.shopping,
        inventory=services.inventory,
        recipes=services.recipes,
        chores=services.chores,
        calendar=services.calendar,
        budget=services.budget,
        notifications=services.notifications,
        devices=services.devices,
        media=services.media,
        integrations=directory,
        contract=dashboard_contract,
    )

    return NuestraCasitaApplication(
        integrations=directory,
        services=services,
        dashboard=dashboard,
    )
    DoctorService,
