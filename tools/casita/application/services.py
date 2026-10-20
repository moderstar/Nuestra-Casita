"""
Household capability services.

Each service depends on the injected IntegrationDirectory and returns only
backend-neutral domain models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar
from zoneinfo import ZoneInfo

from casita.application.coordination import (
    IntegrationDirectory,
    IntegrationFailure,
)
from casita.domain import (
    BudgetSummary,
    CalendarEvent,
    Chore,
    Device,
    Inventory,
    HouseholdTask,
    MealPlanEntry,
    MediaItem,
    Notification,
    Recipe,
    ShoppingList,
)
from casita.integrations import (
    AddShoppingItem,
    Capability,
    ChoreMutationIntegration,
    CompleteChore,
    RemoveShoppingItem,
    ShoppingItemStateChange,
    ShoppingMutationIntegration,
    ShoppingProductOption,
)


RecordType = TypeVar("RecordType")


@dataclass(frozen=True, slots=True)
class ServiceResult(Generic[RecordType]):
    """Return typed domain records and non-fatal integration failures."""

    records: tuple[RecordType, ...]
    refreshed_at: datetime | None
    failures: tuple[IntegrationFailure, ...] = ()


class CapabilityService(Generic[RecordType]):
    """Base service that validates records for one household capability."""

    capability: Capability
    record_type: type[RecordType]

    def __init__(self, integrations: IntegrationDirectory) -> None:
        self._integrations = integrations

    def read(
        self,
        household_id: str,
        *,
        since: datetime | None = None,
    ) -> ServiceResult[RecordType]:
        """Read and type-check records from all selected integrations."""

        result = self._integrations.read(
            household_id,
            self.capability,
            since=since,
        )
        records: list[RecordType] = []
        failures = list(result.failures)

        for record in result.records:
            if isinstance(record, self.record_type):
                records.append(record)
                continue

            failures.append(
                IntegrationFailure(
                    integration_key="application",
                    capability=self.capability,
                    message=(
                        f"Capability {self.capability.value!r} returned "
                        f"unexpected record {type(record).__name__!r}."
                    ),
                )
            )

        return ServiceResult(
            records=tuple(records),
            refreshed_at=result.refreshed_at,
            failures=tuple(failures),
        )


class ShoppingService(CapabilityService[ShoppingList]):
    """Provide normalized household shopping lists."""

    capability = Capability.SHOPPING
    record_type = ShoppingList

    def search_products(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[ShoppingProductOption, ...]:
        """Search bounded backend-neutral product choices."""

        text = query.strip()
        if not 1 <= len(text) <= 80:
            raise ValueError("Product search must contain 1 to 80 characters.")
        if not 1 <= limit <= 25:
            raise ValueError("Product search limit must be between 1 and 25.")
        return self._writer().search_shopping_products(text, limit=limit)

    def add_item(
        self,
        command: AddShoppingItem,
    ) -> ServiceResult[ShoppingList]:
        """Add one live item and return authoritative refreshed lists."""

        if command.quantity <= Decimal("0") or not command.quantity.is_finite():
            raise ValueError("Shopping quantity must be a positive finite decimal.")
        if command.quantity > Decimal("1000000"):
            raise ValueError("Shopping quantity is too large.")
        if command.product_id is None and command.note.strip() == "":
            raise ValueError("A product or a note is required.")
        self._writer().add_shopping_item(command)
        return self.read(command.household_id)

    def set_purchased(
        self,
        command: ShoppingItemStateChange,
    ) -> ServiceResult[ShoppingList]:
        """Set Grocy's purchased marker and return refreshed lists."""

        self._writer().set_shopping_item_purchased(command)
        return self.read(command.household_id)

    def remove_item(
        self,
        command: RemoveShoppingItem,
    ) -> ServiceResult[ShoppingList]:
        """Remove one exact live item and return refreshed lists."""

        self._writer().remove_shopping_item(command)
        return self.read(command.household_id)

    def _writer(self) -> ShoppingMutationIntegration:
        integrations = self._integrations.integrations_for(self.capability)
        writers = tuple(
            item for item in integrations
            if isinstance(item, ShoppingMutationIntegration)
        )
        if len(writers) != 1:
            raise RuntimeError("Shopping mutations require exactly one owner.")
        return writers[0]


class InventoryService(CapabilityService[Inventory]):
    """Provide normalized household inventory projections."""

    capability = Capability.INVENTORY
    record_type = Inventory


class RecipeService(CapabilityService[Recipe]):
    """Provide normalized household recipes."""

    capability = Capability.RECIPES
    record_type = Recipe


class ChoreService(CapabilityService[Chore]):
    """Provide normalized household chores."""

    capability = Capability.CHORES
    record_type = Chore

    def complete(self, command: CompleteChore) -> ServiceResult[Chore]:
        """Record activity through the owner and return refreshed chores."""

        integrations = self._integrations.integrations_for(self.capability)
        writers = tuple(
            item for item in integrations
            if isinstance(item, ChoreMutationIntegration)
        )
        if len(writers) != 1:
            raise RuntimeError("Chore mutations require exactly one owner.")
        writers[0].complete_chore(command)
        return self.read(command.household_id)


class MealPlanService(CapabilityService[MealPlanEntry]):
    """Provide normalized read-only household meal plans."""

    capability = Capability.MEAL_PLAN
    record_type = MealPlanEntry


class TaskService(CapabilityService[HouseholdTask]):
    """Provide normalized read-only household tasks."""

    capability = Capability.TASKS
    record_type = HouseholdTask


class CalendarService(CapabilityService[CalendarEvent]):
    """Provide normalized household calendar events."""

    capability = Capability.CALENDAR
    record_type = CalendarEvent

    def today(
        self,
        household_id: str,
        timezone: str,
        *,
        now: datetime,
    ) -> ServiceResult[CalendarEvent]:
        """Return events overlapping the household's current local date."""

        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError(
                "Dashboard assembly requires a timezone-aware current time."
            )

        result = self.read(household_id)
        local_timezone = ZoneInfo(timezone)
        local_date = now.astimezone(local_timezone).date()
        events = []
        failures = list(result.failures)

        for event in result.records:
            if (
                event.starts_at.tzinfo is None
                or event.starts_at.utcoffset() is None
                or event.ends_at.tzinfo is None
                or event.ends_at.utcoffset() is None
            ):
                failures.append(
                    IntegrationFailure(
                        integration_key="application",
                        capability=self.capability,
                        message=(
                            f"Calendar event {event.id!r} must use "
                            "timezone-aware timestamps."
                        ),
                    )
                )
                continue

            if (
                event.starts_at.astimezone(local_timezone).date()
                <= local_date
                <= event.ends_at.astimezone(local_timezone).date()
            ):
                events.append(event)

        return ServiceResult(
            records=tuple(
                sorted(events, key=lambda event: event.starts_at)
            ),
            refreshed_at=result.refreshed_at,
            failures=tuple(failures),
        )


class BudgetService(CapabilityService[BudgetSummary]):
    """Provide normalized household budget summaries."""

    capability = Capability.BUDGET
    record_type = BudgetSummary


class NotificationService(CapabilityService[Notification]):
    """Provide normalized household notifications."""

    capability = Capability.NOTIFICATIONS
    record_type = Notification


class DeviceService(CapabilityService[Device]):
    """Provide normalized household devices and current states."""

    capability = Capability.DEVICES
    record_type = Device


class MediaService(CapabilityService[MediaItem]):
    """Provide normalized media selected for household display."""

    capability = Capability.MEDIA
    record_type = MediaItem
