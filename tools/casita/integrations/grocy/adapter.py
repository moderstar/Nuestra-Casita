"""Grocy read adapter for the Nuestra Casita integration contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from casita.integrations import (
    Capability,
    CapabilityData,
    CommandSyncResult,
    DiagnosticCheck,
    HealthStatus,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationRuntime,
    IntegrationSnapshot,
    FieldDifference,
    PlannedChange,
    ReadRequest,
    SyncAction,
    SyncRequest,
    SynchronizationPlan,
    SynchronizationResult,
)
from casita.integrations.grocy.client import GrocyApiClient
from casita.integrations.grocy.mapping import (
    map_chores,
    map_inventory,
    map_recipes,
    map_shopping_lists,
    rows_by_id,
)


class GrocyReader(Protocol):
    """Minimal Grocy transport required by the read adapter."""

    def get(self, endpoint: str) -> Any:
        """Return one decoded Grocy API response."""


class GrocyReadAdapter:
    """Translate Grocy 4.6 API responses into household domain models."""

    descriptor = IntegrationDescriptor(
        key="grocy",
        display_name="Grocy",
        capabilities=frozenset(
            {
                Capability.SHOPPING,
                Capability.INVENTORY,
                Capability.RECIPES,
                Capability.CHORES,
            }
        ),
        version="4.6",
    )

    def __init__(
        self,
        client: GrocyReader,
        *,
        timezone_name: str = "UTC",
        sync_runner: Callable[..., Any] | None = None,
        sync_planner: Callable[..., Any] | None = None,
        sync_applier: Callable[..., Any] | None = None,
    ) -> None:
        self._client = client
        self._timezone = ZoneInfo(timezone_name)
        self._sync_runner = sync_runner
        self._sync_planner = sync_planner
        self._sync_applier = sync_applier
        self._native_plans: dict[
            str,
            tuple[SynchronizationPlan, Any, Any],
        ] = {}

    @classmethod
    def from_credentials(
        cls,
        base_url: str,
        api_key: str,
        *,
        timezone_name: str = "UTC",
    ) -> GrocyReadAdapter:
        """Construct an adapter with the shared Grocy HTTP client."""

        return cls(
            GrocyApiClient(base_url, api_key),
            timezone_name=timezone_name,
        )

    def health(self) -> IntegrationHealth:
        """Check whether the configured Grocy API is reachable."""

        checked_at = datetime.now(timezone.utc)

        try:
            self._client.get("/system/info")
        except Exception as error:
            return IntegrationHealth(
                integration_key=self.descriptor.key,
                status=HealthStatus.UNAVAILABLE,
                checked_at=checked_at,
                message=str(error) or error.__class__.__name__,
            )

        return IntegrationHealth(
            integration_key=self.descriptor.key,
            status=HealthStatus.HEALTHY,
            checked_at=checked_at,
        )

    def diagnose(self) -> tuple[DiagnosticCheck, ...]:
        """Run Grocy-owned connectivity and API authentication checks."""

        try:
            self._client.get("/system/info")
        except Exception as error:
            message = str(error) or error.__class__.__name__
            reachable = getattr(error, "response", None) is not None
            return (
                DiagnosticCheck(
                    "Grocy Connection",
                    reachable,
                    message,
                ),
                DiagnosticCheck(
                    "API Authentication",
                    False,
                    message,
                ),
                DiagnosticCheck(
                    "Adapter Connectivity",
                    False,
                    message,
                ),
            )

        return (
            DiagnosticCheck("Grocy Connection", True),
            DiagnosticCheck("API Authentication", True),
            DiagnosticCheck("Adapter Connectivity", True),
        )

    def synchronize(
        self,
        resource: str,
        *,
        apply: bool = False,
    ) -> CommandSyncResult:
        """Delegate declarative synchronization to the established workflow."""

        if self._sync_runner is None:
            raise RuntimeError("Grocy synchronization is not configured.")

        plans = self._sync_runner(resource, apply=apply)
        return CommandSyncResult(
            integration_key=self.descriptor.key,
            resource=resource,
            applied=apply,
            plans=plans,
        )

    def plan(self, request: SyncRequest) -> SynchronizationPlan:
        """Translate one native Grocy plan into the platform contract."""

        if self._sync_planner is None:
            raise RuntimeError(
                "Grocy structured synchronization planning is not configured."
            )

        resource, native_plan = self._sync_planner(request.resource)
        plan_id = uuid4().hex
        plan = SynchronizationPlan(
            integration_key=self.descriptor.key,
            resource=request.resource,
            generated_at=datetime.now(timezone.utc),
            changes=self._map_native_changes(native_plan),
            plan_id=plan_id,
        )
        self._native_plans[plan_id] = (
            plan,
            resource,
            native_plan,
        )
        return plan

    def apply(
        self,
        plan: SynchronizationPlan,
    ) -> SynchronizationResult:
        """Apply the exact native Grocy plan represented by a public plan."""

        if self._sync_applier is None:
            raise RuntimeError(
                "Grocy structured synchronization execution is not configured."
            )

        prepared = self._native_plans.get(plan.plan_id)

        if prepared is None or prepared[0] != plan:
            raise ValueError(
                "Synchronization plan was not prepared by this Grocy adapter."
            )

        _, resource, native_plan = prepared
        counts = self._sync_applier(resource, native_plan)
        del self._native_plans[plan.plan_id]
        return SynchronizationResult(
            integration_key=self.descriptor.key,
            resource=plan.resource,
            created=counts["created"],
            updated=counts["updated"],
            matched=counts["matched"],
            completed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _map_native_changes(
        native_plan: dict[str, list[dict[str, Any]]],
    ) -> tuple[PlannedChange, ...]:
        changes = []

        for operation, action in (
            ("update", SyncAction.UPDATE),
            ("create", SyncAction.CREATE),
            ("match", SyncAction.MATCH),
        ):
            for item in native_plan[operation]:
                display_name = str(item["name"])
                differences = tuple(
                    FieldDifference(
                        field=str(
                            difference.get("api_field")
                            or difference.get("label")
                            or "field"
                        ),
                        current_value=difference.get("grocy_value"),
                        desired_value=difference.get("catalog_value"),
                    )
                    for difference in item.get("changes", ())
                )
                changes.append(
                    PlannedChange(
                        identity=display_name.strip().casefold(),
                        display_name=display_name,
                        action=action,
                        differences=differences,
                    )
                )

        return tuple(changes)

    def runtime(self) -> IntegrationRuntime:
        """Return dashboard-safe Grocy status and aggregate counts."""

        try:
            system_info = self._client.get("/system/info")
            products = self._client.get("/objects/products")
            recipes = self._client.get(
                "/objects/recipes?query[]=type=normal"
            )
            locations = self._client.get("/objects/locations")
        except Exception as error:
            return IntegrationRuntime(
                integration_key=self.descriptor.key,
                display_name=self.descriptor.display_name,
                connected=False,
                version=self.descriptor.version,
                errors=(str(error) or error.__class__.__name__,),
            )

        for name, rows in (
            ("products", products),
            ("recipes", recipes),
            ("locations", locations),
        ):
            if not isinstance(rows, list):
                return IntegrationRuntime(
                    integration_key=self.descriptor.key,
                    display_name=self.descriptor.display_name,
                    connected=False,
                    version=self.descriptor.version,
                    errors=(f"Grocy {name} response was not a list.",),
                )

        info = system_info if isinstance(system_info, dict) else {}
        grocy_version = info.get("grocy_version", {})

        if isinstance(grocy_version, dict):
            version = str(
                grocy_version.get("Version")
                or grocy_version.get("version")
                or self.descriptor.version
            )
        else:
            version = str(grocy_version or self.descriptor.version)

        sqlite_version = str(
            info.get("sqlite_version")
            or info.get("database")
            or ""
        )

        return IntegrationRuntime(
            integration_key=self.descriptor.key,
            display_name=self.descriptor.display_name,
            connected=True,
            version=version,
            database=(
                f"SQLite {sqlite_version}"
                if sqlite_version
                else "SQLite"
            ),
            metrics=(
                ("products", len(products)),
                ("recipes", len(recipes)),
                ("locations", len(locations)),
            ),
        )

    def read(self, request: ReadRequest) -> IntegrationSnapshot:
        """Read requested capabilities and return normalized domain records."""

        unsupported = request.capabilities - self.descriptor.capabilities

        if unsupported:
            names = ", ".join(
                sorted(capability.value for capability in unsupported)
            )
            raise ValueError(
                f"Grocy does not provide requested capabilities: {names}."
            )

        generated_at = datetime.now(timezone.utc)
        cache: dict[str, list[dict[str, Any]]] = {}

        def rows(endpoint: str) -> list[dict[str, Any]]:
            if endpoint not in cache:
                response = self._client.get(endpoint)

                if not isinstance(response, list):
                    raise ValueError(
                        f"Grocy endpoint {endpoint!r} did not return a list."
                    )

                if not all(isinstance(row, dict) for row in response):
                    raise ValueError(
                        f"Grocy endpoint {endpoint!r} returned an "
                        "invalid record."
                    )

                cache[endpoint] = response

            return cache[endpoint]

        data = []

        for capability in sorted(
            request.capabilities,
            key=lambda item: item.value,
        ):
            if capability == Capability.INVENTORY:
                records = (
                    map_inventory(
                        request.household_id,
                        rows("/stock"),
                        rows_by_id(rows("/objects/quantity_units")),
                        measured_at=generated_at,
                    ),
                )
            elif capability == Capability.SHOPPING:
                records = map_shopping_lists(
                    request.household_id,
                    rows("/objects/shopping_lists"),
                    rows("/objects/shopping_list"),
                    rows_by_id(rows("/objects/products")),
                    rows_by_id(rows("/objects/quantity_units")),
                    self._timezone,
                )
            elif capability == Capability.RECIPES:
                records = map_recipes(
                    request.household_id,
                    rows("/objects/recipes?query[]=type=normal"),
                    rows("/objects/recipes_pos"),
                    rows_by_id(rows("/objects/products")),
                    rows_by_id(rows("/objects/quantity_units")),
                )
            elif capability == Capability.CHORES:
                records = map_chores(
                    request.household_id,
                    rows("/objects/chores"),
                    rows("/chores"),
                    self._timezone,
                )
            else:
                raise AssertionError(
                    f"Unhandled Grocy capability {capability.value!r}."
                )

            data.append(
                CapabilityData(
                    capability=capability,
                    records=records,
                    refreshed_at=generated_at,
                )
            )

        return IntegrationSnapshot(
            integration_key=self.descriptor.key,
            household_id=request.household_id,
            generated_at=generated_at,
            data=tuple(data),
        )
