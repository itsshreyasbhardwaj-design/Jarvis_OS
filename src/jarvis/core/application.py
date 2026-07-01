"""
JARVIS OS Application Orchestrator
====================================
The top-level entry point that wires together all modules, manages the
event bus, service registry, and lifecycle manager.

This class is the only place in the codebase that knows about every module.
All inter-module communication happens through the EventBus.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import TYPE_CHECKING, Any

from loguru import logger

from jarvis.core.event_bus import EventBus, SystemShutdownEvent, SystemStartupEvent
from jarvis.core.lifecycle import AppState, HealthStatus, LifecycleManager
from jarvis.core.service_registry import ServiceRegistry

if TYPE_CHECKING:
    from jarvis.ai.agent import JarvisAgent
    from jarvis.ai.llm_router import LLMRouter
    from jarvis.config.settings import Settings
    from jarvis.memory.memory_manager import MemoryManager


class JarvisOS:
    """
    JARVIS OS — Top-level application orchestrator.

    Responsibilities:
    1. Load configuration
    2. Wire the event bus and service registry
    3. Register all module implementations
    4. Start the lifecycle manager
    5. Handle OS signals (SIGINT, SIGTERM)
    6. Run the main event loop
    7. Shut down gracefully

    Usage:
        app = JarvisOS()
        app.run()                    # Blocking (production)
        # or
        await app.start()            # Async (testing)
        await app.stop()
    """

    def __init__(self) -> None:
        self._bus = EventBus()
        self._registry = ServiceRegistry()
        self._lifecycle = LifecycleManager()
        self._shutdown_event = asyncio.Event()
        self._agent: JarvisAgent | None = None
        self._signal_tasks: set[asyncio.Task[None]] = set()

    # --- Public API ---

    def run(self) -> None:
        """
        Start JARVIS OS and block until shutdown.
        This is the main entry point for production use.
        """
        try:
            asyncio.run(self._run_async())
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            sys.exit(1)

    async def start(self) -> None:
        """Async start (for testing and programmatic use)."""
        await self._initialize()
        await self._lifecycle.start_all()
        await self._bus.publish(SystemStartupEvent())

    async def stop(self, reason: str = "user_request") -> None:
        """Async stop."""
        logger.info(f"Shutdown requested: {reason}")
        await self._bus.publish(SystemShutdownEvent(reason=reason))
        await self._lifecycle.stop_all()
        await self._bus.stop()
        self._shutdown_event.set()

    # --- Properties ---

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def registry(self) -> ServiceRegistry:
        return self._registry

    @property
    def state(self) -> AppState:
        return self._lifecycle.state

    async def health(self) -> list[dict[str, Any]]:
        """Return health status of all modules."""
        statuses = await self._lifecycle.check_health()
        return [
            {
                "module": s.module,
                "healthy": s.healthy,
                "message": s.message,
            }
            for s in statuses
        ]

    # --- Internal ---

    async def _run_async(self) -> None:
        """Full async application loop."""
        self._register_signal_handlers()
        await self._initialize()
        await self._lifecycle.start_all()
        await self._bus.publish(SystemStartupEvent())

        logger.info("JARVIS OS is running. Press Ctrl+C to stop.")
        await self._shutdown_event.wait()

        await self._lifecycle.stop_all()
        await self._bus.stop()

    async def _initialize(self) -> None:
        """
        Bootstrap phase: configure logging, load settings, register modules.
        This is the only method that imports concrete implementations.
        All modules are registered here by interface, keeping the rest of
        the codebase decoupled.
        """
        # Start event bus first (other modules need it)
        await self._bus.start()

        # Register the bus and registry themselves as services
        self._registry.register_instance(EventBus, self._bus)
        self._registry.register_instance(ServiceRegistry, self._registry)
        self._registry.register_instance(LifecycleManager, self._lifecycle)

        # Lazy imports of module implementations
        # This prevents circular imports and allows selective loading
        from jarvis.config.settings import Settings
        settings = Settings()
        self._registry.register_instance(Settings, settings)

        from jarvis.logging.setup import configure_logging
        configure_logging(settings)

        logger.info(
            f"JARVIS OS v{_get_version()} starting in "
            f"{settings.environment} mode"
        )

        # Register all service implementations
        self._register_services(settings)

        # Wire the conversational brain (memory + LLM router + agent + tools)
        self._register_brain(settings)

        # Register modules for lifecycle management
        self._register_modules()

    def _register_services(self, settings: Settings) -> None:
        """Register all service implementations with the DI container."""
        # AI Provider — degrade gracefully if the selected provider's optional
        # dependency (e.g. anthropic, litellm) is not installed in this environment.
        import importlib

        from jarvis.ai.providers.base import AIProvider
        provider_map = {
            "claude": "jarvis.ai.providers.claude.ClaudeProvider",
            "openai": "jarvis.ai.providers.openai.OpenAIProvider",
            "gemini": "jarvis.ai.providers.gemini.GeminiProvider",
            "local": "jarvis.ai.providers.local.LocalProvider",
        }
        provider_path = provider_map.get(settings.ai.provider, provider_map["claude"])
        module_path, class_name = provider_path.rsplit(".", 1)
        try:
            provider_module = importlib.import_module(module_path)
            provider_cls = getattr(provider_module, class_name)
            self._registry.register(AIProvider, provider_cls)
        except ImportError as e:
            logger.warning(
                "AI provider '{}' unavailable ({}); skipping registration",
                settings.ai.provider,
                e,
            )

        # Memory
        from jarvis.memory.conversation_history import ConversationHistory
        from jarvis.memory.long_term import LongTermMemory
        from jarvis.memory.short_term import ShortTermMemory
        self._registry.register(ShortTermMemory, ShortTermMemory)
        self._registry.register(LongTermMemory, LongTermMemory)
        self._registry.register(ConversationHistory, ConversationHistory)

        # Security
        from jarvis.desktop.permissions import PermissionManager
        from jarvis.security.audit_log import AuditLogger
        self._registry.register(PermissionManager, PermissionManager)
        self._registry.register(AuditLogger, AuditLogger)

        logger.debug("Services registered")

    def _register_modules(self) -> None:
        """Register feature lifecycle modules (self-register in later increments)."""

    def _register_brain(self, settings: Settings) -> None:
        """Wire the conversational brain: memory + LLM router + tools + agent."""
        from jarvis.ai.agent import JarvisAgent
        from jarvis.ai.conversation import ConversationEngine
        from jarvis.ai.llm_router import LLMRouter
        from jarvis.ai.tools import build_tool_executor
        from jarvis.desktop.permissions import PermissionManager
        from jarvis.integrations.web_search import WebSearch
        from jarvis.memory.memory_manager import MemoryManager

        memory = MemoryManager(settings)
        router = LLMRouter(settings)
        web_search = WebSearch()
        permissions = PermissionManager(require_confirmation=False, safe_mode=False)
        tools = build_tool_executor(web_search=web_search, permissions=permissions)
        engine = ConversationEngine(router, memory)
        self._agent = JarvisAgent(engine, tools=tools)

        self._registry.register_instance(MemoryManager, memory)
        self._registry.register_instance(LLMRouter, router)
        self._registry.register_instance(JarvisAgent, self._agent)

        # Persistent memory opens on startup and flushes on shutdown.
        self._lifecycle.register(_BrainModule(memory, router))
        logger.debug("Brain registered (LLM live={})", router.is_live())

    async def ask(self, text: str) -> str:
        """Send one text turn to JARVIS and return the reply.

        Requires the app to be started — the brain is wired during startup.
        """
        if self._agent is None:
            raise RuntimeError("JARVIS is not started; call start() before ask().")
        return await self._agent.handle(text)

    def _register_signal_handlers(self) -> None:
        """Register OS signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        def _handle_signal(sig: signal.Signals) -> None:
            logger.info(f"Received signal {sig.name}")
            task = loop.create_task(self.stop(reason=sig.name))
            self._signal_tasks.add(task)
            task.add_done_callback(self._signal_tasks.discard)

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda s=sig: _handle_signal(s)
            )


class _BrainModule:
    """Lifecycle wrapper that opens/closes persistent memory with the app."""

    def __init__(self, memory: MemoryManager, router: LLMRouter) -> None:
        self._memory = memory
        self._router = router

    @property
    def name(self) -> str:
        return "ai.brain"

    @property
    def startup_priority(self) -> int:
        return 25

    @property
    def critical(self) -> bool:
        return False

    async def start(self) -> None:
        await self._memory.initialize(title="JARVIS session")

    async def stop(self) -> None:
        await self._memory.close()

    async def health_check(self) -> HealthStatus:
        mode = "live LLM" if self._router.is_live() else "offline"
        detail = "persistent" if self._memory.is_persistent else "working-memory only"
        return HealthStatus(
            module=self.name,
            healthy=True,
            message=f"brain ready ({mode}, {detail})",
        )


def _get_version() -> str:
    try:
        from importlib.metadata import version
        return version("jarvis-os")
    except Exception:
        return "0.1.0-dev"
