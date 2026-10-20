"""Grocy read adapter for the Nuestra Casita integration contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from casita.integrations import (
    AppliedChange,
    AddShoppingItem,
    Capability,
    CapabilityData,
    ChoreDefinition,
    ChoreUserOption,
    DiagnosticCheck,
    CompleteChore,
    DeactivateChore,
    HealthStatus,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationRuntime,
    IntegrationSnapshot,
    OperationConflict,
    OperationNotFound,
    FieldDifference,
    PlannedChange,
    ReadRequest,
    RemoveShoppingItem,
    ShoppingItemStateChange,
    ShoppingProductOption,
    SyncAction,
    SyncRequest,
    SynchronizationPlan,
    SynchronizationResult,
    UpdateChoreDefinition,
)
from casita.integrations.grocy.client import GrocyApiClient
from casita.integrations.grocy.mapping import (
    domain_id,
    datetime_value,
    map_chores,
    map_inventory,
    map_meal_plan,
    map_recipes,
    map_shopping_lists,
    map_tasks,
    rows_by_id,
)


class GrocyReader(Protocol):
    """Minimal Grocy transport required by the read adapter."""

    def get(self, endpoint: str) -> Any:
        """Return one decoded Grocy API response."""

    def post(self, endpoint: str, payload: Mapping[str, Any]) -> Any:
        """Create or execute one explicitly supported operation."""

    def put(self, endpoint: str, payload: Mapping[str, Any]) -> Any:
        """Update one explicitly supported object."""

    def delete(self, endpoint: str) -> Any:
        """Delete one explicitly supported object."""


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
                Capability.MEAL_PLAN,
                Capability.TASKS,
            }
        ),
        version="4.6",
    )

    def __init__(
        self,
        client: GrocyReader,
        *,
        timezone_name: str = "UTC",
        sync_planner: Callable[..., Any] | None = None,
        sync_applier: Callable[..., Any] | None = None,
    ) -> None:
        self._client = client
        self._timezone = ZoneInfo(timezone_name)
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

    def plan(self, request: SyncRequest) -> SynchronizationPlan:
        """Translate one native Grocy plan into the platform contract."""

        if self._sync_planner is None:
            raise RuntimeError(
                "Grocy structured synchronization planning is not configured."
            )

        resource, native_plan = self._sync_planner(request.resource)
        metadata = native_plan.get("_metadata", {})
        plan_id = uuid4().hex
        plan = SynchronizationPlan(
            integration_key=self.descriptor.key,
            resource=request.resource,
            generated_at=datetime.now(timezone.utc),
            changes=self._map_native_changes(native_plan),
            plan_id=plan_id,
            resource_label=str(metadata.get("resource_label", "")),
            catalog_count=int(metadata.get("catalog_count", 0)),
            backend_count=int(metadata.get("backend_count", 0)),
            lookups_loaded=bool(metadata.get("lookups_loaded", False)),
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
            changes=tuple(
                AppliedChange(
                    display_name=change["display_name"],
                    action=SyncAction(change["operation"]),
                )
                for change in counts.get("changes", ())
            ),
            resource_label=str(counts.get("resource_label", "")),
            lookups_loaded=bool(counts.get("lookups_loaded", False)),
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
                        label=str(
                            difference.get(
                                "label",
                                difference.get("api_field", "Field"),
                            )
                        ),
                        current_display=str(
                            difference.get("grocy_display", "")
                        ),
                        desired_display=str(
                            difference.get("catalog_display", "")
                        ),
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

    def search_shopping_products(
        self,
        query: str,
        *,
        limit: int,
    ) -> tuple[ShoppingProductOption, ...]:
        """Return active Grocy products with their purchase unit."""

        products = self._rows("/objects/products")
        units = rows_by_id(self._rows("/objects/quantity_units"))
        needle = query.casefold()
        options = []

        for product in products:
            name = str(product.get("name") or "").strip()
            if needle not in name.casefold():
                continue
            if str(product.get("active", 1)).strip().casefold() in {"0", "false"}:
                continue
            native_unit_id = product.get("qu_id_purchase")
            unit = units.get(str(native_unit_id).strip())
            if native_unit_id is None or unit is None:
                continue
            options.append(
                ShoppingProductOption(
                    id=domain_id("product", product.get("id")),
                    name=name,
                    unit_id=domain_id("quantity-unit", native_unit_id),
                    unit=str(unit.get("name") or "").strip(),
                )
            )

        return tuple(
            sorted(options, key=lambda item: item.name.casefold())[:limit]
        )

    def add_shopping_item(self, command: AddShoppingItem) -> None:
        """Create one exact live shopping item through the generic API."""

        shopping_list = self._resolve(
            "shopping-list",
            command.shopping_list_id,
            self._rows("/objects/shopping_lists"),
        )
        product_id = None
        unit_id = None

        if command.product_id is not None:
            product = self._resolve(
                "product",
                command.product_id,
                self._rows("/objects/products"),
            )
            product_id = product["id"]
            native_purchase_unit = product.get("qu_id_purchase")
            if native_purchase_unit is None:
                raise OperationConflict("The selected product has no purchase unit.")
            expected_unit_id = domain_id("quantity-unit", native_purchase_unit)
            if command.unit_id not in (None, expected_unit_id):
                raise OperationConflict(
                    "The selected quantity unit is not compatible with this product."
                )
            self._resolve(
                "quantity-unit",
                expected_unit_id,
                self._rows("/objects/quantity_units"),
            )
            unit_id = native_purchase_unit
        elif command.unit_id is not None:
            raise OperationConflict("A note-only item cannot select a quantity unit.")

        self._client.post(
            "/objects/shopping_list",
            {
                "shopping_list_id": shopping_list["id"],
                "product_id": product_id,
                "amount": format(command.quantity, "f"),
                "qu_id": unit_id,
                "note": command.note.strip(),
                "done": 0,
            },
        )

    def set_shopping_item_purchased(
        self,
        command: ShoppingItemStateChange,
    ) -> None:
        """Set Grocy's list-only done marker without a stock booking."""

        item = self._shopping_item(command.shopping_list_id, command.item_id)
        desired = 1 if command.purchased else 0
        current = str(item.get("done", 0)).strip().casefold() in {
            "1", "true", "yes", "on"
        }
        if current != command.purchased:
            self._client.put(
                f"/objects/shopping_list/{item['id']}",
                {"done": desired},
            )

    def remove_shopping_item(self, command: RemoveShoppingItem) -> None:
        """Remove one exact item after verifying its list membership."""

        item = self._shopping_item(command.shopping_list_id, command.item_id)
        self._client.delete(f"/objects/shopping_list/{item['id']}")

    def complete_chore(self, command: CompleteChore) -> None:
        """Record a normal Grocy chore execution using the API-key user."""

        chore = self._resolve(
            "chore",
            command.chore_id,
            self._rows("/objects/chores"),
        )
        self._client.post(
            f"/chores/{chore['id']}/execute",
            {"tracked_time": "", "done_by": ""},
        )

    def list_chore_users(self) -> tuple[ChoreUserOption, ...]:
        """Return Grocy users as opaque assignment choices."""

        return tuple(
            sorted(
                (
                    ChoreUserOption(
                        id=domain_id("person", user["id"]),
                        display_name=str(
                            user.get("display_name")
                            or user.get("username")
                            or ""
                        ).strip(),
                    )
                    for user in self._rows("/users")
                    if user.get("id") is not None
                ),
                key=lambda item: item.display_name.casefold(),
            )
        )

    def create_chore(self, command: ChoreDefinition) -> None:
        """Create one native chore and calculate its first assignment."""

        chores = self._rows("/objects/chores")
        if any(
            str(row.get("name") or "").strip().casefold()
            == command.name.strip().casefold()
            for row in chores
        ):
            raise OperationConflict("A chore with that name already exists.")
        payload = self._chore_payload(command)
        result = self._client.post("/objects/chores", payload)
        if not isinstance(result, dict) or result.get("created_object_id") is None:
            raise ValueError("Grocy did not return the created chore identity.")
        self._client.post(
            "/chores/executions/calculate-next-assignments",
            {"chore_id": result["created_object_id"]},
        )

    def update_chore(self, command: UpdateChoreDefinition) -> None:
        """Update managed fields while preserving history and locked dates."""

        chores = self._rows("/objects/chores")
        chore = self._resolve("chore", command.chore_id, chores)
        if any(
            row.get("id") != chore.get("id")
            and str(row.get("name") or "").strip().casefold()
            == command.name.strip().casefold()
            for row in chores
        ):
            raise OperationConflict("A chore with that name already exists.")

        logs = self._rows("/objects/chores_log")
        has_history = any(
            str(row.get("chore_id")) == str(chore["id"])
            for row in logs
        )
        current_start = datetime_value(chore.get("start_date"), self._timezone)
        requested_start = command.start_at.astimezone(timezone.utc).replace(microsecond=0)
        if has_history and current_start != requested_start:
            raise OperationConflict(
                "The start date cannot change after a chore has execution history."
            )

        payload = self._chore_payload(command)
        if has_history:
            payload.pop("start_date", None)
        self._client.put(f"/objects/chores/{chore['id']}", payload)
        self._client.post(
            "/chores/executions/calculate-next-assignments",
            {"chore_id": chore["id"]},
        )

    def deactivate_chore(self, command: DeactivateChore) -> None:
        """Deactivate a chore because native deletion cascades its history."""

        chore = self._resolve(
            "chore", command.chore_id, self._rows("/objects/chores")
        )
        if str(chore.get("active", 1)).strip().casefold() not in {
            "0", "false", "no", "off"
        }:
            self._client.put(f"/objects/chores/{chore['id']}", {"active": 0})

    def _chore_payload(
        self,
        command: ChoreDefinition | UpdateChoreDefinition,
    ) -> dict[str, Any]:
        users = self._rows("/users")
        native_user_ids = [
            self._resolve("person", user_id, users)["id"]
            for user_id in command.assignment_user_ids
        ]
        return {
            "name": command.name.strip(),
            "description": command.description.strip(),
            "period_type": command.schedule_type,
            "period_interval": command.schedule_interval,
            "period_days": command.schedule_day,
            "period_config": ",".join(command.schedule_weekdays),
            "start_date": command.start_at.astimezone(self._timezone).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "assignment_type": command.assignment_type,
            "assignment_config": ",".join(str(item) for item in native_user_ids),
            "active": 1 if command.active else 0,
        }

    def _shopping_item(
        self,
        shopping_list_id: str,
        item_id: str,
    ) -> Mapping[str, Any]:
        shopping_list = self._resolve(
            "shopping-list",
            shopping_list_id,
            self._rows("/objects/shopping_lists"),
        )
        item = self._resolve(
            "shopping-item",
            item_id,
            self._rows("/objects/shopping_list"),
        )
        if str(item.get("shopping_list_id", 1)) != str(shopping_list["id"]):
            raise OperationConflict("The shopping item is not on the selected list.")
        return item

    def _rows(self, endpoint: str) -> list[dict[str, Any]]:
        response = self._client.get(endpoint)
        if not isinstance(response, list) or not all(
            isinstance(item, dict) for item in response
        ):
            raise ValueError(f"Grocy endpoint {endpoint!r} returned invalid data.")
        return response

    @staticmethod
    def _resolve(
        resource: str,
        opaque_id: str,
        rows: Iterable[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        matches = [
            row for row in rows
            if row.get("id") is not None
            and domain_id(resource, row.get("id")) == opaque_id
        ]
        if len(matches) != 1:
            raise OperationNotFound(f"The selected {resource} no longer exists.")
        return matches[0]

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
                users = rows_by_id(rows("/users"))
                records = map_chores(
                    request.household_id,
                    rows("/objects/chores"),
                    rows("/chores"),
                    self._timezone,
                    rows("/objects/chores_log"),
                    users,
                )
            elif capability == Capability.MEAL_PLAN:
                records = map_meal_plan(
                    request.household_id,
                    rows("/objects/meal_plan"),
                    rows_by_id(rows("/objects/meal_plan_sections")),
                    rows_by_id(rows("/objects/recipes?query[]=type=normal")),
                    rows_by_id(rows("/objects/products")),
                    rows_by_id(rows("/objects/quantity_units")),
                )
            elif capability == Capability.TASKS:
                records = map_tasks(
                    request.household_id,
                    rows("/objects/tasks"),
                    rows_by_id(rows("/objects/task_categories")),
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
