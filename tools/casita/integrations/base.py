"""
Backend-neutral contracts for Nuestra Casita integrations.

An integration translates between an external system and the domain models.
Vendor clients, endpoints, and payloads remain behind the integration
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, TypeAlias, runtime_checkable

from casita.domain import (
    BudgetSummary,
    CalendarEvent,
    Chore,
    Device,
    Household,
    Inventory,
    HouseholdTask,
    MealPlanEntry,
    MediaItem,
    Notification,
    Person,
    Recipe,
    ShoppingList,
)


DomainRecord: TypeAlias = (
    Household
    | Person
    | ShoppingList
    | Inventory
    | HouseholdTask
    | MealPlanEntry
    | Recipe
    | Chore
    | CalendarEvent
    | BudgetSummary
    | Notification
    | Device
    | MediaItem
)


class Capability(str, Enum):
    """Describe a household capability supplied by an integration."""

    HOUSEHOLD = "household"
    PEOPLE = "people"
    SHOPPING = "shopping"
    INVENTORY = "inventory"
    RECIPES = "recipes"
    CHORES = "chores"
    MEAL_PLAN = "meal-plan"
    TASKS = "tasks"
    CALENDAR = "calendar"
    BUDGET = "budget"
    NOTIFICATIONS = "notifications"
    DEVICES = "devices"
    MEDIA = "media"


class HealthStatus(str, Enum):
    """Describe an integration's current availability."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IntegrationDescriptor:
    """Describe an installed integration without exposing its client."""

    key: str
    display_name: str
    capabilities: frozenset[Capability]
    version: str = ""


@dataclass(frozen=True, slots=True)
class IntegrationHealth:
    """Represent the latest connectivity state of an integration."""

    integration_key: str
    status: HealthStatus
    checked_at: datetime
    message: str = ""


@dataclass(frozen=True, slots=True)
class ReadRequest:
    """Request normalized domain data from an integration."""

    household_id: str
    capabilities: frozenset[Capability]
    since: datetime | None = None


@dataclass(frozen=True, slots=True)
class CapabilityData:
    """Group normalized records for one integration capability."""

    capability: Capability
    records: tuple[DomainRecord, ...]
    refreshed_at: datetime


@dataclass(frozen=True, slots=True)
class IntegrationSnapshot:
    """Return normalized records from one integration read."""

    integration_key: str
    household_id: str
    generated_at: datetime
    data: tuple[CapabilityData, ...]


@runtime_checkable
class Integration(Protocol):
    """Common read boundary implemented by each external system adapter."""

    @property
    def descriptor(self) -> IntegrationDescriptor:
        """Return stable integration metadata and supported capabilities."""

    def health(self) -> IntegrationHealth:
        """Return current adapter and backend availability."""

    def read(self, request: ReadRequest) -> IntegrationSnapshot:
        """Translate backend data into Nuestra Casita domain records."""


class SyncAction(str, Enum):
    """Describe one declarative synchronization decision."""

    CREATE = "create"
    UPDATE = "update"
    MATCH = "match"


@dataclass(frozen=True, slots=True)
class FieldDifference:
    """Describe one backend-neutral field difference."""

    field: str
    current_value: object
    desired_value: object
    label: str = ""
    current_display: str = ""
    desired_display: str = ""


@dataclass(frozen=True, slots=True)
class PlannedChange:
    """Describe one object in a declarative synchronization plan."""

    identity: str
    display_name: str
    action: SyncAction
    differences: tuple[FieldDifference, ...] = ()


@dataclass(frozen=True, slots=True)
class SyncRequest:
    """Request a plan for one integration-owned declarative resource."""

    household_id: str
    resource: str


@dataclass(frozen=True, slots=True)
class SynchronizationPlan:
    """Represent a dry-run plan without vendor payload details."""

    integration_key: str
    resource: str
    generated_at: datetime
    changes: tuple[PlannedChange, ...]
    plan_id: str = ""
    resource_label: str = ""
    catalog_count: int = 0
    backend_count: int = 0
    lookups_loaded: bool = False


@dataclass(frozen=True, slots=True)
class AppliedChange:
    """Describe one successfully applied synchronization change."""

    display_name: str
    action: SyncAction


@dataclass(frozen=True, slots=True)
class SynchronizationResult:
    """Summarize successful execution of a synchronization plan."""

    integration_key: str
    resource: str
    created: int
    updated: int
    matched: int
    completed_at: datetime
    changes: tuple[AppliedChange, ...] = ()
    resource_label: str = ""
    lookups_loaded: bool = False


@runtime_checkable
class SynchronizingIntegration(Integration, Protocol):
    """Optional contract for integrations with declarative sync resources."""

    def plan(self, request: SyncRequest) -> SynchronizationPlan:
        """Build a dry-run plan using the integration's resource adapters."""

    def apply(self, plan: SynchronizationPlan) -> SynchronizationResult:
        """Apply a previously generated plan through the owning integration."""

@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    """Describe one backend-neutral integration diagnostic."""

    name: str
    passed: bool
    message: str = ""


@runtime_checkable
class DiagnosableIntegration(Integration, Protocol):
    """Expose actionable integration checks to application services."""

    def diagnose(self) -> tuple[DiagnosticCheck, ...]:
        """Run adapter-owned connectivity and authentication checks."""


@dataclass(frozen=True, slots=True)
class IntegrationRuntime:
    """Expose normalized runtime metadata for application presentation."""

    integration_key: str
    display_name: str
    connected: bool
    version: str = ""
    database: str = ""
    metrics: tuple[tuple[str, int], ...] = ()
    errors: tuple[str, ...] = ()


@runtime_checkable
class RuntimeInspectableIntegration(Integration, Protocol):
    """Provide dashboard-safe runtime information through the adapter."""

    def runtime(self) -> IntegrationRuntime:
        """Return normalized integration status and aggregate metrics."""


class OperationNotFound(ValueError):
    """Report that an opaque household object no longer exists."""


class OperationConflict(ValueError):
    """Report a safe conflict with current authoritative state."""


@dataclass(frozen=True, slots=True)
class ShoppingProductOption:
    """Expose a bounded product choice without backend identifiers."""

    id: str
    name: str
    unit_id: str
    unit: str


@dataclass(frozen=True, slots=True)
class AddShoppingItem:
    """Request one validated live shopping-list item."""

    household_id: str
    shopping_list_id: str
    quantity: Decimal
    product_id: str | None = None
    unit_id: str | None = None
    note: str = ""


@dataclass(frozen=True, slots=True)
class ShoppingItemStateChange:
    """Request one explicit shopping-item state transition."""

    household_id: str
    shopping_list_id: str
    item_id: str
    purchased: bool


@dataclass(frozen=True, slots=True)
class RemoveShoppingItem:
    """Request removal of one exact shopping-list item."""

    household_id: str
    shopping_list_id: str
    item_id: str


@dataclass(frozen=True, slots=True)
class CompleteChore:
    """Request a normal completion of one existing chore."""

    household_id: str
    chore_id: str


@runtime_checkable
class ShoppingMutationIntegration(Integration, Protocol):
    """Optional narrow write contract for live shopping activity."""

    def search_shopping_products(
        self,
        query: str,
        *,
        limit: int,
    ) -> tuple[ShoppingProductOption, ...]:
        """Return bounded product choices."""

    def add_shopping_item(self, command: AddShoppingItem) -> None:
        """Add one product or note item."""

    def set_shopping_item_purchased(
        self,
        command: ShoppingItemStateChange,
    ) -> None:
        """Set the non-stock-affecting purchased marker."""

    def remove_shopping_item(self, command: RemoveShoppingItem) -> None:
        """Remove one exact live item."""


@runtime_checkable
class ChoreMutationIntegration(Integration, Protocol):
    """Optional narrow write contract for live chore activity."""

    def complete_chore(self, command: CompleteChore) -> None:
        """Record a normal completion while preserving its definition."""
