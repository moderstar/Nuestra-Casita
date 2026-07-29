"""
Nuestra Casita household domain models.

These immutable models describe household concepts without exposing the
schemas, identifiers, or API vocabulary of any connected application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Map a Nuestra Casita object back to one integration-owned record."""

    integration: str
    external_id: str
    external_type: str = ""


@dataclass(frozen=True, slots=True)
class Money:
    """Represent a currency amount without using binary floating point."""

    amount: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class Household:
    """Represent the household that owns all platform data."""

    id: str
    name: str
    timezone: str
    members: tuple[str, ...] = ()
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class Person:
    """Represent one household member or trusted participant."""

    id: str
    household_id: str
    display_name: str
    email: str = ""
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class ShoppingItem:
    """Represent one requested item on a household shopping list."""

    id: str
    name: str
    quantity: Decimal | None = None
    unit: str = ""
    checked: bool = False
    note: str = ""
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class ShoppingList:
    """Represent a household shopping list and its current items."""

    id: str
    household_id: str
    name: str
    items: tuple[ShoppingItem, ...] = ()
    updated_at: datetime | None = None
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class InventoryItem:
    """Represent one household inventory item."""

    id: str
    name: str
    quantity: Decimal
    unit: str
    location: str = ""
    expires_on: date | None = None
    low_stock: bool = False
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class Inventory:
    """Represent the household's current inventory projection."""

    household_id: str
    items: tuple[InventoryItem, ...] = ()
    measured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RecipeIngredient:
    """Represent one backend-neutral recipe ingredient."""

    name: str
    quantity: Decimal | None = None
    unit: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class Recipe:
    """Represent a household recipe definition."""

    id: str
    household_id: str
    name: str
    description: str = ""
    servings: Decimal = Decimal("1")
    ingredients: tuple[RecipeIngredient, ...] = ()
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class Chore:
    """Represent a household chore and its user-facing due state."""

    id: str
    household_id: str
    name: str
    description: str = ""
    due_at: datetime | None = None
    assigned_person_id: str | None = None
    completed: bool = False
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """Represent an event shown on the household calendar."""

    id: str
    household_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    location: str = ""
    participant_ids: tuple[str, ...] = ()
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class BudgetSummary:
    """Represent a concise household budget projection."""

    household_id: str
    period_start: date
    period_end: date
    income: Money
    spent: Money
    available: Money
    updated_at: datetime | None = None
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class Notification:
    """Represent a platform notification for household members."""

    id: str
    household_id: str
    title: str
    message: str
    created_at: datetime
    severity: str = "info"
    read: bool = False
    source_references: tuple[SourceReference, ...] = ()


class DeviceState(str, Enum):
    """Describe the normalized availability of a household device."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Device:
    """Represent a device or controllable household endpoint."""

    id: str
    household_id: str
    name: str
    kind: str
    state: DeviceState = DeviceState.UNKNOWN
    attributes: tuple[tuple[str, str], ...] = ()
    source_references: tuple[SourceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class MediaItem:
    """Represent media selected for a household-facing experience."""

    id: str
    household_id: str
    title: str
    media_type: str
    captured_at: datetime | None = None
    preview_uri: str = ""
    source_references: tuple[SourceReference, ...] = ()
