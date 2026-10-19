"""Tests for backend registration and resolution."""

from unittest import TestCase

from casita.bootstrap import (
    BackendProvider,
    BackendRegistry,
    BackendResolver,
)


class FakeBackendProvider:
    """Minimal provider used to verify backend discovery."""

    def __init__(self, key: str) -> None:
        self.key = key
        self.planner = object()
        self.executor = object()

    @property
    def integrations(self):
        return ()

    @property
    def capability_owners(self):
        return {}

    def catalog_planner(self, directory):
        return self.planner

    def catalog_executor(self, directory):
        return self.executor


class BackendRegistryTests(TestCase):
    def test_registers_and_resolves_provider(self):
        provider = FakeBackendProvider("fake")
        registry = BackendRegistry()
        registry.register(provider)

        self.assertIs(registry.get("fake"), provider)
        self.assertEqual(registry.providers, (provider,))
        self.assertIs(registry.by_key["fake"], provider)

    def test_rejects_duplicate_provider_key(self):
        registry = BackendRegistry()
        registry.register(FakeBackendProvider("fake"))

        with self.assertRaisesRegex(ValueError, "more than once"):
            registry.register(FakeBackendProvider("fake"))

    def test_rejects_invalid_provider_keys(self):
        for key in ("", " fake "):
            with self.subTest(key=key):
                registry = BackendRegistry()

                with self.assertRaises(ValueError):
                    registry.register(FakeBackendProvider(key))

    def test_rejects_unknown_backend(self):
        registry = BackendRegistry()

        with self.assertRaisesRegex(ValueError, "is not registered"):
            registry.get("missing")

    def test_provider_contract_is_runtime_checkable(self):
        self.assertIsInstance(FakeBackendProvider("fake"), BackendProvider)


class BackendResolverTests(TestCase):
    def test_resolves_default_backend(self):
        first = FakeBackendProvider("first")
        default = FakeBackendProvider("default")
        registry = BackendRegistry()
        registry.register(first)
        registry.register(default)

        resolver = BackendResolver(registry, default_key="default")

        self.assertEqual(resolver.default_key, "default")
        self.assertIs(resolver.resolve(), default)

    def test_explicit_backend_replaces_default_without_service_changes(self):
        default = FakeBackendProvider("default")
        replacement = FakeBackendProvider("replacement")
        registry = BackendRegistry()
        registry.register(default)
        registry.register(replacement)
        resolver = BackendResolver(registry, default_key="default")

        selected = resolver.resolve("replacement")

        self.assertIs(selected, replacement)
        self.assertIs(selected.catalog_planner(object()), replacement.planner)
        self.assertIs(
            selected.catalog_executor(object()),
            replacement.executor,
        )
