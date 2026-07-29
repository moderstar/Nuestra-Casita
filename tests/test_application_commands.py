"""Tests for backend-neutral application command services."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from casita.application import (
    DoctorService,
    IntegrationDirectory,
    SyncService,
)
from casita.integrations import (
    Capability,
    CommandSyncResult,
    DiagnosticCheck,
    HealthStatus,
    IntegrationDescriptor,
    IntegrationHealth,
    IntegrationSnapshot,
)


class FakeCommandIntegration:
    """Implement command contracts without a concrete backend."""

    descriptor = IntegrationDescriptor(
        key="fake",
        display_name="Fake",
        capabilities=frozenset({Capability.INVENTORY}),
    )

    def health(self):
        return IntegrationHealth(
            integration_key="fake",
            status=HealthStatus.HEALTHY,
            checked_at=datetime.now(timezone.utc),
        )

    def read(self, request):
        return IntegrationSnapshot(
            integration_key="fake",
            household_id=request.household_id,
            generated_at=datetime.now(timezone.utc),
            data=(),
        )

    def synchronize(self, resource, *, apply=False):
        return CommandSyncResult("fake", resource, apply, {"match": []})

    def diagnose(self):
        return (DiagnosticCheck("Fake Connection", True),)


class SyncServiceTests(TestCase):
    def test_routes_through_integration_contract(self):
        directory = IntegrationDirectory((FakeCommandIntegration(),))
        service = SyncService(
            directory,
            owner="fake",
            resources=("all", "products"),
        )

        result = service.synchronize("products", apply=True)

        self.assertEqual(result.integration_key, "fake")
        self.assertEqual(result.resource, "products")
        self.assertTrue(result.applied)


class DoctorServiceTests(TestCase):
    def test_reports_local_and_adapter_checks(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog = root / "catalog"
            tools = root / "tools"
            catalog.mkdir()
            tools.mkdir()
            (catalog / "things.csv").write_text(
                "name\n",
                encoding="utf-8",
            )
            directory = IntegrationDirectory((FakeCommandIntegration(),))
            service = DoctorService(
                directory,
                configuration_exists=lambda: True,
                catalog_root=catalog,
                resources={
                    "things": {"catalog_file": "things.csv"},
                },
                payload_registry_valid=lambda: None,
                resource_registry_valid=lambda: None,
            )

            report = service.run()

        self.assertTrue(report.passed)
        self.assertEqual(
            [check.name for check in report.checks],
            [
                "Configuration",
                "Required Directories",
                "Catalog Integrity",
                "Resource Registry",
                "Payload Registry",
                "Fake Connection",
            ],
        )
