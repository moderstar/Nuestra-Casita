"""Backend-neutral application services for Nuestra Casita."""

from casita.application.coordination import (
    CapabilityRead,
    IntegrationDirectory,
    IntegrationFailure,
)
from casita.application.catalog import (
    CatalogApplicationService,
    CatalogOperationResult,
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
    SynchronizationExecutor,
    SynchronizationPlanner,
    SynchronizationRun,
)

__all__ = [
    "BudgetService",
    "CatalogApplicationService",
    "CatalogOperationResult",
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
    "InventoryService",
    "MediaService",
    "NotificationService",
    "RecipeService",
    "ServiceResult",
    "ShoppingService",
    "SynchronizationPlanner",
    "SynchronizationExecutor",
    "SynchronizationApplicationService",
    "SynchronizationRun",
]
