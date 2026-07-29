"""
Versioned internal contract for the future kitchen dashboard.

The dashboard consumes this aggregate only. It never imports an integration
client or relies on a vendor-specific record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from casita.domain import (
    BudgetSummary,
    CalendarEvent,
    Chore,
    Device,
    Household,
    Inventory,
    MediaItem,
    Notification,
    Recipe,
    ShoppingList,
)
from casita.integrations import Capability
from casita.integrations import IntegrationRuntime


class DashboardSection(str, Enum):
    """Name the stable sections in the household dashboard contract."""

    TODAY = "today"
    SHOPPING = "shopping"
    INVENTORY = "inventory"
    MEALS = "meals"
    CHORES = "chores"
    BUDGET = "budget"
    HOME = "home"
    MEDIA = "media"
    NOTIFICATIONS = "notifications"


@dataclass(frozen=True, slots=True)
class RefreshPolicy:
    """Define cache freshness without prescribing a cache implementation."""

    fresh_for_seconds: int
    stale_for_seconds: int
    refresh_in_background: bool = True


@dataclass(frozen=True, slots=True)
class SectionContract:
    """Describe ownership and freshness for one dashboard section."""

    section: DashboardSection
    capabilities: frozenset[Capability]
    refresh: RefreshPolicy
    required: bool = False


@dataclass(frozen=True, slots=True)
class DashboardContract:
    """Version the collection of sections exposed to dashboard clients."""

    version: str
    sections: tuple[SectionContract, ...]


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """Aggregate backend-neutral household data for one dashboard render."""

    contract_version: str
    generated_at: datetime
    household: Household
    today: tuple[CalendarEvent, ...] = ()
    shopping_lists: tuple[ShoppingList, ...] = ()
    inventory: Inventory | None = None
    recipes: tuple[Recipe, ...] = ()
    chores: tuple[Chore, ...] = ()
    budget: BudgetSummary | None = None
    devices: tuple[Device, ...] = ()
    media: tuple[MediaItem, ...] = ()
    notifications: tuple[Notification, ...] = ()
    stale_sections: frozenset[DashboardSection] = frozenset()


@dataclass(frozen=True, slots=True)
class Dashboard:
    """Present platform status alongside the household snapshot."""

    snapshot: DashboardSnapshot
    integrations: tuple[IntegrationRuntime, ...] = ()
    configuration_valid: bool = True
    last_synchronization: datetime | None = None
    missing_resources: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


DEFAULT_DASHBOARD_CONTRACT = DashboardContract(
    version="1",
    sections=(
        SectionContract(
            DashboardSection.TODAY,
            frozenset({Capability.CALENDAR}),
            RefreshPolicy(300, 3600),
            required=True,
        ),
        SectionContract(
            DashboardSection.SHOPPING,
            frozenset({Capability.SHOPPING}),
            RefreshPolicy(30, 300),
            required=True,
        ),
        SectionContract(
            DashboardSection.INVENTORY,
            frozenset({Capability.INVENTORY}),
            RefreshPolicy(300, 1800),
        ),
        SectionContract(
            DashboardSection.MEALS,
            frozenset({Capability.RECIPES}),
            RefreshPolicy(300, 3600),
        ),
        SectionContract(
            DashboardSection.CHORES,
            frozenset({Capability.CHORES}),
            RefreshPolicy(60, 600),
        ),
        SectionContract(
            DashboardSection.BUDGET,
            frozenset({Capability.BUDGET}),
            RefreshPolicy(900, 7200),
        ),
        SectionContract(
            DashboardSection.HOME,
            frozenset({Capability.DEVICES}),
            RefreshPolicy(10, 60),
        ),
        SectionContract(
            DashboardSection.MEDIA,
            frozenset({Capability.MEDIA}),
            RefreshPolicy(3600, 86400),
        ),
        SectionContract(
            DashboardSection.NOTIFICATIONS,
            frozenset({Capability.NOTIFICATIONS}),
            RefreshPolicy(30, 300),
        ),
    ),
)
