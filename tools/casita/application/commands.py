"""Backend-neutral application command services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from casita.application.coordination import IntegrationDirectory
from casita.integrations import (
    CommandSyncResult,
    CommandSynchronizingIntegration,
    DiagnosableIntegration,
    DiagnosticCheck,
)


@dataclass(frozen=True, slots=True)
class DoctorReport:
    """Collect ordered platform checks for command-line presentation."""

    checks: tuple[DiagnosticCheck, ...]

    @property
    def passed(self) -> bool:
        """Return whether every diagnostic check passed."""

        return all(check.passed for check in self.checks)


class SyncService:
    """Coordinate declarative synchronization through integration contracts."""

    def __init__(
        self,
        integrations: IntegrationDirectory,
        *,
        owner: str,
        resources: tuple[str, ...],
    ) -> None:
        self._integrations = integrations
        self._owner = owner
        self._resources = resources

    @property
    def resources(self) -> tuple[str, ...]:
        """Return accepted resource names in orchestration order."""

        return self._resources

    def synchronize(
        self,
        resource: str,
        *,
        apply: bool = False,
    ) -> CommandSyncResult:
        """Run one synchronization command through its owning integration."""

        integration = self._integrations.get(self._owner)

        if not isinstance(integration, CommandSynchronizingIntegration):
            raise RuntimeError(
                f"Integration {self._owner!r} does not support synchronization."
            )

        return integration.synchronize(resource, apply=apply)


class MaintenanceService:
    """Preserve legacy maintenance operations behind the application layer."""

    def __init__(
        self,
        *,
        show_lookups: Callable[[], object],
        validate_catalog: Callable[[], object],
        export_products: Callable[[], object],
    ) -> None:
        self._show_lookups = show_lookups
        self._validate_catalog = validate_catalog
        self._export_products = export_products

    def lookups(self):
        """Display integration lookups through the configured operation."""

        return self._show_lookups()

    def validate(self):
        """Validate catalogs through the configured operation."""

        return self._validate_catalog()

    def export(self, resource: str):
        """Export one backward-compatible integration resource."""

        if resource != "products":
            raise ValueError(f"Unsupported export resource {resource!r}.")

        return self._export_products()


class DoctorService:
    """Validate platform configuration and registered integration resources."""

    def __init__(
        self,
        integrations: IntegrationDirectory,
        *,
        configuration_exists: Callable[[], bool],
        catalog_root: Path,
        resources: Mapping[str, Mapping[str, object]],
        payload_registry_valid: Callable[[], None],
        resource_registry_valid: Callable[[], None],
    ) -> None:
        self._integrations = integrations
        self._configuration_exists = configuration_exists
        self._catalog_root = catalog_root
        self._resources = resources
        self._payload_registry_valid = payload_registry_valid
        self._resource_registry_valid = resource_registry_valid

    def run(self) -> DoctorReport:
        """Run deterministic local checks followed by adapter diagnostics."""

        checks = [
            DiagnosticCheck(
                "Configuration",
                self._configuration_exists(),
                "Create .env with GROCY_URL and GROCY_API_KEY."
                if not self._configuration_exists()
                else "",
            ),
            self._directory_check(),
            self._catalog_check(),
            self._call_check(
                "Resource Registry",
                self._resource_registry_valid,
            ),
            self._call_check(
                "Payload Registry",
                self._payload_registry_valid,
            ),
        ]

        for integration in self._integrations.integrations:
            if isinstance(integration, DiagnosableIntegration):
                checks.extend(integration.diagnose())
                continue

            health = integration.health()
            checks.append(
                DiagnosticCheck(
                    f"{integration.descriptor.display_name} Connection",
                    health.status.value == "healthy",
                    health.message,
                )
            )

        return DoctorReport(tuple(checks))

    def _directory_check(self) -> DiagnosticCheck:
        required = (self._catalog_root, self._catalog_root.parent / "tools")
        missing = [str(path) for path in required if not path.is_dir()]
        return DiagnosticCheck(
            "Required Directories",
            not missing,
            f"Missing: {', '.join(missing)}" if missing else "",
        )

    def _catalog_check(self) -> DiagnosticCheck:
        missing = []

        for name, resource in self._resources.items():
            filename = str(resource.get("catalog_file", "")).strip()

            if not filename or not (self._catalog_root / filename).is_file():
                missing.append(name)

        return DiagnosticCheck(
            "Catalog Integrity",
            not missing,
            f"Missing catalogs: {', '.join(sorted(missing))}"
            if missing
            else "",
        )

    @staticmethod
    def _call_check(
        name: str,
        check: Callable[[], None],
    ) -> DiagnosticCheck:
        try:
            check()
        except Exception as error:
            return DiagnosticCheck(
                name,
                False,
                str(error) or error.__class__.__name__,
            )

        return DiagnosticCheck(name, True)
