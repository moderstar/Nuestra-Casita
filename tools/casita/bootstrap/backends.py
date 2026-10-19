"""Backend registration and resolution for the composition root."""

from __future__ import annotations

from types import MappingProxyType
from typing import Protocol, runtime_checkable

from casita.application import (
    CatalogExecutor,
    CatalogPlanner,
    IntegrationDirectory,
)
from casita.integrations import Capability, Integration


@runtime_checkable
class BackendProvider(Protocol):
    """Construct integrations and catalog components for one backend."""

    @property
    def key(self) -> str:
        """Return the stable backend registration key."""

    @property
    def integrations(self) -> tuple[Integration, ...]:
        """Return the backend's application-scoped integrations."""

    @property
    def capability_owners(self) -> dict[Capability, tuple[str, ...]]:
        """Return explicit capability ownership for the backend."""

    def catalog_planner(
        self,
        directory: IntegrationDirectory,
    ) -> CatalogPlanner:
        """Build the backend's catalog planner."""

    def catalog_executor(
        self,
        directory: IntegrationDirectory,
    ) -> CatalogExecutor:
        """Build the backend's catalog executor."""


class BackendRegistry:
    """Store available backend providers by stable key."""

    def __init__(self) -> None:
        self._providers: dict[str, BackendProvider] = {}

    @property
    def providers(self) -> tuple[BackendProvider, ...]:
        """Return providers in registration order."""

        return tuple(self._providers.values())

    @property
    def by_key(self):
        """Return a read-only view of registered providers."""

        return MappingProxyType(self._providers)

    def register(self, provider: BackendProvider) -> None:
        """Register one validated provider."""

        if not isinstance(provider, BackendProvider):
            raise TypeError("Backend provider does not satisfy its contract.")

        raw_key = provider.key
        key = raw_key.strip()

        if not key:
            raise ValueError("Backend provider keys cannot be blank.")

        if key != raw_key:
            raise ValueError(
                "Backend provider keys cannot contain surrounding whitespace."
            )

        if key in self._providers:
            raise ValueError(f"Backend {key!r} is registered more than once.")

        self._providers[key] = provider

    def get(self, key: str) -> BackendProvider:
        """Return one registered provider by key."""

        try:
            return self._providers[key]
        except KeyError as error:
            raise ValueError(f"Backend {key!r} is not registered.") from error


class BackendResolver:
    """Resolve an explicitly selected or default backend provider."""

    def __init__(
        self,
        registry: BackendRegistry,
        *,
        default_key: str,
    ) -> None:
        self._registry = registry
        self._default_key = default_key

    @property
    def default_key(self) -> str:
        """Return the configured default backend key."""

        return self._default_key

    def resolve(self, key: str | None = None) -> BackendProvider:
        """Resolve the requested backend, falling back to the default."""

        return self._registry.get(key or self._default_key)
