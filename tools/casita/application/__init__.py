"""Backend-neutral application services for Nuestra Casita."""

from casita.application.coordination import (
    CapabilityRead,
    IntegrationDirectory,
    IntegrationFailure,
)
from casita.application.catalog import (
    CatalogApplicationService,
    CatalogExecutionResult,
    CatalogExecutor,
    CatalogOperation,
    CatalogOperationResult,
    CatalogPlan,
    CatalogPlanner,
    IntegrationCatalogExecutor,
    IntegrationCatalogPlanner,
)
from casita.application.commands import (
    DoctorReport,
    DoctorService,
    MaintenanceService,
)
from casita.application.dashboard import DashboardService
from casita.application.services import (
    BudgetService,
    CalendarService,
    ChoreService,
    DeviceService,
    InventoryService,
    MediaService,
    NotificationService,
    RecipeService,
    ServiceResult,
    ShoppingService,
)
from casita.application.synchronization import (
    SynchronizationApplicationService,
    SynchronizationRun,
)

__all__ = [
    "BudgetService",
    "CatalogApplicationService",
    "CatalogExecutionResult",
    "CatalogExecutor",
    "CatalogOperation",
    "CatalogOperationResult",
    "CatalogPlan",
    "CatalogPlanner",
    "CalendarService",
    "CapabilityRead",
    "ChoreService",
    "DashboardService",
    "DeviceService",
    "DoctorReport",
    "DoctorService",
    "MaintenanceService",
    "IntegrationDirectory",
    "IntegrationFailure",
    "IntegrationCatalogExecutor",
    "IntegrationCatalogPlanner",
    "InventoryService",
    "MediaService",
    "NotificationService",
    "RecipeService",
    "ServiceResult",
    "ShoppingService",
    "SynchronizationApplicationService",
    "SynchronizationRun",
]
