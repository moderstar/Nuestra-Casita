"""
Household capability services.

Each service depends on the injected IntegrationDirectory and returns only
backend-neutral domain models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    MediaItem,
    Notification,
    Recipe,
    ShoppingList,
)
from casita.integrations import Capability


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
