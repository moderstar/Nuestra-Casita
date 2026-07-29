"""Integration contracts for external Nuestra Casita systems."""

from casita.integrations.base import (
    ApplyResult,
    Capability,
    CapabilityData,
    FieldDifference,
    HealthStatus,
    Integration,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationSnapshot,
    PlannedChange,
    ReadRequest,
    SyncAction,
    SyncRequest,
    SynchronizationPlan,
    SynchronizingIntegration,
)

__all__ = [
    "ApplyResult",
    "Capability",
    "CapabilityData",
    "FieldDifference",
    "HealthStatus",
    "Integration",
    "IntegrationDescriptor",
    "IntegrationHealth",
    "IntegrationSnapshot",
    "PlannedChange",
    "ReadRequest",
    "SyncAction",
    "SyncRequest",
    "SynchronizationPlan",
    "SynchronizingIntegration",
]
