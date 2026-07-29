"""
Backend-neutral contracts for Nuestra Casita integrations.

An integration translates between an external system and the domain models.
Vendor clients, endpoints, and payloads remain behind the integration
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, TypeAlias, runtime_checkable

from casita.domain import (
    BudgetSummary,
    CalendarEvent,
    Chore,
    Device,
    Household,
    Inventory,
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


@dataclass(frozen=True, slots=True)
class ApplyResult:
    """Summarize an applied synchronization plan."""

    integration_key: str
    resource: str
    created: int
    updated: int
    matched: int
    completed_at: datetime


@runtime_checkable
class SynchronizingIntegration(Integration, Protocol):
    """Optional contract for integrations with declarative sync resources."""

    def plan(self, request: SyncRequest) -> SynchronizationPlan:
        """Build a dry-run plan using the integration's resource adapters."""

    def apply(self, plan: SynchronizationPlan) -> ApplyResult:
        """Apply a previously generated plan through the owning integration."""
