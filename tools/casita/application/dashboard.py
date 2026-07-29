"""
Dashboard snapshot assembly.

DashboardService coordinates household capability services and returns the
versioned internal dashboard contract without importing backend adapters.
"""

from __future__ import annotations

from datetime import datetime, timezone

from casita.application.coordination import IntegrationDirectory
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
from casita.dashboard import (
    DEFAULT_DASHBOARD_CONTRACT,
    DashboardContract,
    DashboardSection,
    DashboardSnapshot,
)
from casita.domain import (
    BudgetSummary,
    Household,
    Inventory,
    InventoryItem,
)


class DashboardService:
    """Assemble one complete backend-neutral household dashboard snapshot."""

    def __init__(
        self,
        *,
        shopping: ShoppingService,
        inventory: InventoryService,
        recipes: RecipeService,
        chores: ChoreService,
        calendar: CalendarService,
        budget: BudgetService,
        notifications: NotificationService,
        devices: DeviceService,
        media: MediaService,
        contract: DashboardContract = DEFAULT_DASHBOARD_CONTRACT,
    ) -> None:
        self._shopping = shopping
        self._inventory = inventory
        self._recipes = recipes
        self._chores = chores
        self._calendar = calendar
        self._budget = budget
        self._notifications = notifications
        self._devices = devices
        self._media = media
        self._contract = contract

    @classmethod
    def from_integrations(
        cls,
        integrations: IntegrationDirectory,
        *,
        contract: DashboardContract = DEFAULT_DASHBOARD_CONTRACT,
    ) -> DashboardService:
        """Create the default service composition for injected integrations."""

        return cls(
            shopping=ShoppingService(integrations),
            inventory=InventoryService(integrations),
            recipes=RecipeService(integrations),
            chores=ChoreService(integrations),
            calendar=CalendarService(integrations),
            budget=BudgetService(integrations),
            notifications=NotificationService(integrations),
            devices=DeviceService(integrations),
            media=MediaService(integrations),
            contract=contract,
        )

    def build(
        self,
        household: Household,
        *,
        now: datetime | None = None,
    ) -> DashboardSnapshot:
        """Read household capabilities and assemble a dashboard snapshot."""

        generated_at = now or datetime.now(timezone.utc)
        calendar = self._calendar.today(
            household.id,
            household.timezone,
            now=generated_at,
        )
        shopping = self._shopping.read(household.id)
        inventory = self._inventory.read(household.id)
        recipes = self._recipes.read(household.id)
        chores = self._chores.read(household.id)
        budget = self._budget.read(household.id)
        devices = self._devices.read(household.id)
        media = self._media.read(household.id)
        notifications = self._notifications.read(household.id)
        section_results = {
            DashboardSection.TODAY: calendar,
            DashboardSection.SHOPPING: shopping,
            DashboardSection.INVENTORY: inventory,
            DashboardSection.MEALS: recipes,
            DashboardSection.CHORES: chores,
            DashboardSection.BUDGET: budget,
            DashboardSection.HOME: devices,
            DashboardSection.MEDIA: media,
            DashboardSection.NOTIFICATIONS: notifications,
        }
        stale_sections = frozenset(
            section
            for section, result in section_results.items()
            if result.failures
        )

        return DashboardSnapshot(
            contract_version=self._contract.version,
            generated_at=generated_at,
            household=household,
            today=calendar.records,
            shopping_lists=shopping.records,
            inventory=self._merge_inventory(
                household.id,
                inventory,
            ),
            recipes=recipes.records,
            chores=chores.records,
            budget=self._select_budget(budget),
            devices=devices.records,
            media=media.records,
            notifications=notifications.records,
            stale_sections=stale_sections,
        )

    @staticmethod
    def _merge_inventory(
        household_id: str,
        result: ServiceResult[Inventory],
    ) -> Inventory | None:
        """Merge inventory projections from selected capability providers."""

        if not result.records:
            return None

        items: list[InventoryItem] = []
        measured_at = None

        for inventory in result.records:
            items.extend(inventory.items)

            if (
                inventory.measured_at is not None
                and (
                    measured_at is None
                    or inventory.measured_at > measured_at
                )
            ):
                measured_at = inventory.measured_at

        return Inventory(
            household_id=household_id,
            items=tuple(items),
            measured_at=measured_at,
        )

    @staticmethod
    def _select_budget(
        result: ServiceResult[BudgetSummary],
    ) -> BudgetSummary | None:
        """Select the first summary in configured ownership order."""

        if not result.records:
            return None

        return result.records[0]
