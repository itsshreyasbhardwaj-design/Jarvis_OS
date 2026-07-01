"""
Application Lifecycle Manager
==============================
Manages ordered startup and shutdown of all JARVIS OS modules.
Ensures services start in dependency order and shut down gracefully
in reverse order, with timeout enforcement.

Design decisions:
- Ordered phases: Modules declare startup order via STARTUP_ORDER
- Async lifecycle: All start/stop methods are coroutines
- Timeout enforcement: Each module gets a fixed time to start/stop
- Health checks: Modules report readiness after startup
- Graceful degradation: Non-critical modules can fail without killing app
"""

from __future__ import annotations

import asyncio
import enum
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from loguru import logger

# ---------------------------------------------------------------------------
# Lifecycle State
# ---------------------------------------------------------------------------


class AppState(enum.Enum):
    """Overall application state."""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Module Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LifecycleModule(Protocol):
    """
    Protocol that all JARVIS OS modules must implement.

    Modules are started in order of their `startup_priority` (lower = earlier).
    They are stopped in reverse order.
    """

    @property
    def name(self) -> str:
        """Unique module identifier, e.g. 'voice.pipeline'."""
        ...

    @property
    def startup_priority(self) -> int:
        """
        Module startup order. Lower number starts first.
        Recommended ranges:
            0-9:    Core infrastructure (event bus, config, logging)
            10-19:  Security & permissions
            20-29:  Memory & storage
            30-39:  AI providers
            40-49:  Voice pipeline
            50-59:  Desktop & browser automation
            60-69:  Plugin system
            70-79:  UI
            80+:    Background services
        """
        ...

    @property
    def critical(self) -> bool:
        """
        If True, startup failure will abort the entire application.
        If False, the module will be skipped and a warning logged.
        """
        ...

    async def start(self) -> None:
        """Initialize and start the module."""
        ...

    async def stop(self) -> None:
        """Gracefully stop the module and release resources."""
        ...

    async def health_check(self) -> HealthStatus:
        """Return current module health."""
        ...


# ---------------------------------------------------------------------------
# Health Status
# ---------------------------------------------------------------------------


@dataclass
class HealthStatus:
    """Result of a module health check."""
    module: str
    healthy: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.monotonic)


# ---------------------------------------------------------------------------
# Lifecycle Manager
# ---------------------------------------------------------------------------


class LifecycleManager:
    """
    Manages the startup and shutdown of all registered modules.

    Usage:
        manager = LifecycleManager()
        manager.register(EventBusModule())
        manager.register(MemoryModule())
        manager.register(VoiceModule())

        await manager.start_all()    # Starts in priority order
        await manager.stop_all()     # Stops in reverse priority order
    """

    STARTUP_TIMEOUT_SECONDS = 30.0
    STOP_TIMEOUT_SECONDS = 10.0

    def __init__(self) -> None:
        self._modules: list[LifecycleModule] = []
        self._started: list[LifecycleModule] = []
        self._state = AppState.INITIALIZING
        self._start_time: float | None = None

    # --- Registration ---

    def register(self, module: LifecycleModule) -> None:
        """Register a module for lifecycle management."""
        self._modules.append(module)
        # Keep sorted by startup_priority
        self._modules.sort(key=lambda m: m.startup_priority)
        logger.debug(
            f"Lifecycle registered: {module.name} "
            f"(priority={module.startup_priority}, critical={module.critical})"
        )

    # --- Startup ---

    async def start_all(self) -> None:
        """
        Start all registered modules in priority order.
        Critical modules that fail will abort startup.
        """
        self._state = AppState.STARTING
        self._start_time = time.monotonic()
        logger.info(f"Starting {len(self._modules)} modules...")

        for module in self._modules:
            success = await self._start_module(module)
            if not success and module.critical:
                logger.critical(
                    f"Critical module '{module.name}' failed to start. Aborting."
                )
                await self.stop_all()
                self._state = AppState.ERROR
                raise RuntimeError(
                    f"Failed to start critical module: {module.name}"
                )

        self._state = AppState.RUNNING
        elapsed = time.monotonic() - self._start_time
        logger.success(
            f"JARVIS OS started in {elapsed:.2f}s "
            f"({len(self._started)}/{len(self._modules)} modules active)"
        )

    async def _start_module(self, module: LifecycleModule) -> bool:
        """Start a single module with timeout."""
        try:
            logger.info(f"  Starting: {module.name}...")
            start = time.monotonic()
            await asyncio.wait_for(
                module.start(), timeout=self.STARTUP_TIMEOUT_SECONDS
            )
            elapsed = time.monotonic() - start
            self._started.append(module)
            logger.success(f"  ✓ {module.name} ({elapsed:.2f}s)")
            return True
        except TimeoutError:
            logger.error(
                f"  ✗ {module.name} timed out after "
                f"{self.STARTUP_TIMEOUT_SECONDS}s"
            )
            return False
        except Exception as e:
            logger.error(f"  ✗ {module.name} failed: {e}")
            return False

    # --- Shutdown ---

    async def stop_all(self) -> None:
        """
        Stop all started modules in reverse priority order.
        Continues even if individual modules fail to stop cleanly.
        """
        self._state = AppState.STOPPING
        logger.info("Shutting down JARVIS OS...")

        for module in reversed(self._started):
            await self._stop_module(module)

        self._state = AppState.STOPPED
        logger.info("JARVIS OS stopped cleanly.")

    async def _stop_module(self, module: LifecycleModule) -> None:
        """Stop a single module with timeout."""
        try:
            logger.info(f"  Stopping: {module.name}...")
            await asyncio.wait_for(
                module.stop(), timeout=self.STOP_TIMEOUT_SECONDS
            )
            logger.debug(f"  ✓ {module.name} stopped")
        except TimeoutError:
            logger.warning(
                f"  ✗ {module.name} stop timed out after "
                f"{self.STOP_TIMEOUT_SECONDS}s — forcing"
            )
        except Exception as e:
            logger.warning(f"  ✗ {module.name} stop error: {e}")

    # --- Health Checks ---

    async def check_health(self) -> list[HealthStatus]:
        """Run health checks on all started modules."""
        results: list[HealthStatus] = []
        for module in self._started:
            try:
                status = await asyncio.wait_for(
                    module.health_check(), timeout=5.0
                )
                results.append(status)
            except Exception as e:
                results.append(HealthStatus(
                    module=module.name,
                    healthy=False,
                    message=f"Health check error: {e}",
                ))
        return results

    # --- Diagnostics ---

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def uptime(self) -> float | None:
        """Returns uptime in seconds, or None if not running."""
        if self._start_time and self._state == AppState.RUNNING:
            return time.monotonic() - self._start_time
        return None

    def module_summary(self) -> list[dict[str, Any]]:
        """Return summary of all registered modules."""
        return [
            {
                "name": m.name,
                "priority": m.startup_priority,
                "critical": m.critical,
                "started": m in self._started,
            }
            for m in self._modules
        ]
