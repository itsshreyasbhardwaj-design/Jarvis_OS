"""
Service Registry (Dependency Injection Container)
==================================================
A lightweight DI container that manages the lifecycle of all JARVIS OS
services. Services can declare dependencies on other services, and the
registry resolves them automatically.

Design decisions:
- Constructor injection: Dependencies are injected via __init__
- Lazy initialization: Services are only created when first requested
- Singleton scope: One instance per service type (default)
- Interface-based: Register by abstract type, resolve with concrete
- Circular dependency detection: Fails fast with clear error messages
"""

from __future__ import annotations

import inspect
from typing import Any, TypeVar, overload

from loguru import logger

T = TypeVar("T")


class ServiceNotFoundError(Exception):
    """Raised when a requested service has not been registered."""

    def __init__(self, service_type: type) -> None:
        super().__init__(
            f"Service not registered: {service_type.__name__}. "
            "Did you forget to call registry.register()?"
        )


class CircularDependencyError(Exception):
    """Raised when services have circular dependencies."""


class ServiceRegistry:
    """
    Dependency injection container for JARVIS OS services.

    Usage:
        registry = ServiceRegistry()

        # Register concrete implementations
        registry.register(AIProvider, ClaudeProvider)
        registry.register(MemoryStore, SQLiteMemoryStore)

        # Or register pre-built instances (singletons)
        registry.register_instance(EventBus, event_bus)

        # Resolve
        ai: AIProvider = registry.resolve(AIProvider)

        # Auto-wire: registry injects dependencies from __init__ type hints
        service = registry.create(MyComplexService)
    """

    def __init__(self) -> None:
        self._registry: dict[type, type] = {}
        self._instances: dict[type, Any] = {}
        self._factories: dict[type, Any] = {}  # Callable factories
        self._resolving: set[type] = set()     # Circular dep detection

    # --- Registration ---

    def register(
        self,
        interface: type[T],
        implementation: type[T],
        *,
        eager: bool = False,
    ) -> None:
        """
        Register an implementation for an interface.

        Args:
            interface:       Abstract type (used as lookup key)
            implementation:  Concrete class to instantiate
            eager:           If True, create instance immediately
        """
        self._registry[interface] = implementation
        logger.debug(
            f"Registered: {interface.__name__} → {implementation.__name__}"
        )
        if eager:
            self.resolve(interface)

    def register_instance(self, interface: type[T], instance: T) -> None:
        """
        Register a pre-built instance.
        The registry will always return this exact instance.
        """
        self._instances[interface] = instance
        logger.debug(f"Registered instance: {interface.__name__}")

    def register_factory(
        self, interface: type[T], factory: Any
    ) -> None:
        """
        Register a factory callable (called each time the service is resolved).
        Use for transient (non-singleton) services.
        """
        self._factories[interface] = factory
        logger.debug(f"Registered factory: {interface.__name__}")

    # --- Resolution ---

    @overload
    def resolve(self, interface: type[T]) -> T: ...

    def resolve(self, interface: type) -> Any:
        """
        Resolve a service by its interface type.

        Returns a singleton instance, creating it if needed.
        Dependencies declared in __init__ type hints are auto-wired.
        """
        # Return cached singleton
        if interface in self._instances:
            return self._instances[interface]

        # Use factory (transient)
        if interface in self._factories:
            return self._factories[interface]()

        # Instantiate from registry
        if interface not in self._registry:
            raise ServiceNotFoundError(interface)

        # Circular dependency check
        if interface in self._resolving:
            cycle = " → ".join(t.__name__ for t in self._resolving)
            raise CircularDependencyError(
                f"Circular dependency detected: {cycle} → {interface.__name__}"
            )

        self._resolving.add(interface)
        try:
            instance = self.create(self._registry[interface])
            self._instances[interface] = instance  # Cache as singleton
            logger.debug(f"Created singleton: {interface.__name__}")
            return instance
        finally:
            self._resolving.discard(interface)

    def create(self, cls: type[T]) -> T:
        """
        Instantiate a class, auto-wiring its __init__ dependencies.

        Only parameters with type annotations are auto-wired.
        Parameters with default values are skipped if not registered.
        """
        sig = inspect.signature(cls.__init__)
        kwargs: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                if param.default is inspect.Parameter.empty:
                    raise ValueError(
                        f"Cannot auto-wire {cls.__name__}.{param_name}: "
                        "no type annotation and no default value"
                    )
                continue

            # Try to resolve the dependency
            try:
                kwargs[param_name] = self.resolve(annotation)
            except ServiceNotFoundError:
                if param.default is inspect.Parameter.empty:
                    raise
                # Has a default, skip injection
                logger.trace(
                    f"Using default for {cls.__name__}.{param_name}: "
                    f"{annotation.__name__} not registered"
                )

        return cls(**kwargs)

    # --- Queries ---

    def is_registered(self, interface: type) -> bool:
        """Check if a service type is registered."""
        return (
            interface in self._registry
            or interface in self._instances
            or interface in self._factories
        )

    def registered_types(self) -> list[str]:
        """Return names of all registered service types."""
        all_types = (
            set(self._registry.keys())
            | set(self._instances.keys())
            | set(self._factories.keys())
        )
        return sorted(t.__name__ for t in all_types)

    def clear(self) -> None:
        """Reset the registry (useful for testing)."""
        self._registry.clear()
        self._instances.clear()
        self._factories.clear()
        self._resolving.clear()
        logger.debug("ServiceRegistry cleared")
