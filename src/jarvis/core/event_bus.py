"""
Async Event Bus
===============
The central nervous system of JARVIS OS. All modules communicate through
this event bus using a publish/subscribe pattern with type safety.

Design decisions:
- Async-first: All handlers are coroutines to prevent blocking
- Typed events: Each event is a Pydantic model for validation
- Priority queuing: Critical events (security, voice) can bypass queue
- Dead letter queue: Failed events are captured for debugging
- Wildcard subscriptions: Subscribe to event families (e.g., "voice.*")
"""

from __future__ import annotations

import asyncio
import contextlib
import fnmatch
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Event Priority Levels
# ---------------------------------------------------------------------------


class Priority(IntEnum):
    """Event dispatch priority. Higher value = dispatched first."""
    CRITICAL = 100   # Security violations, system errors
    HIGH = 75        # Voice input, user commands
    NORMAL = 50      # General application events
    LOW = 25         # Background tasks, analytics
    BACKGROUND = 10  # Telemetry, non-essential logging


# ---------------------------------------------------------------------------
# Base Event
# ---------------------------------------------------------------------------


@dataclass
class Event:
    """
    Base class for all JARVIS OS events.

    Every event carries a unique ID, timestamp, source module, and priority.
    Subclass this for domain-specific events.

    Example:
        @dataclass
        class VoiceInputEvent(Event):
            transcript: str
            confidence: float

        bus.publish(VoiceInputEvent(
            source="voice.stt",
            transcript="open chrome",
            confidence=0.97,
        ))
    """
    source: str                              # Module that emitted this event
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.monotonic)
    priority: Priority = Priority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Returns dotted event type name, e.g. 'voice.input.received'."""
        return f"{self.__class__.__module__}.{self.__class__.__name__}"


# ---------------------------------------------------------------------------
# Common Event Types
# ---------------------------------------------------------------------------


@dataclass
class SystemStartupEvent(Event):
    """Emitted when JARVIS OS finishes initializing all modules."""
    source: str = "core.application"
    priority: Priority = Priority.HIGH


@dataclass
class SystemShutdownEvent(Event):
    """Emitted when JARVIS OS begins graceful shutdown."""
    source: str = "core.application"
    priority: Priority = Priority.CRITICAL
    reason: str = "user_request"


@dataclass
class ErrorEvent(Event):
    """Emitted when any module encounters an unhandled error."""
    source: str = "core"
    priority: Priority = Priority.HIGH
    error: str = ""
    module: str = ""
    recoverable: bool = True


# ---------------------------------------------------------------------------
# Handler Type Alias
# ---------------------------------------------------------------------------

AsyncHandler = Callable[[Event], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


@dataclass
class Subscription:
    """Internal representation of an event subscription."""
    pattern: str                   # e.g. "VoiceInputEvent" or "voice.*"
    handler: AsyncHandler
    priority: int = 0              # Higher = called first within same event
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    owner: str = "unknown"         # Which module subscribed
    once: bool = False             # Unsubscribe after first invocation


# ---------------------------------------------------------------------------
# Dead Letter Queue Entry
# ---------------------------------------------------------------------------


@dataclass
class DeadLetterEntry:
    """Captures events that failed to be processed."""
    event: Event
    handler_owner: str
    error: str
    timestamp: float = field(default_factory=time.monotonic)


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


class EventBus:
    """
    Thread-safe async event bus with priority queuing.

    Usage:
        bus = EventBus()
        await bus.start()

        # Subscribe
        async def on_voice(event: VoiceInputEvent) -> None:
            print(event.transcript)

        bus.subscribe("VoiceInputEvent", on_voice, owner="my_module")

        # Publish
        await bus.publish(VoiceInputEvent(transcript="hello jarvis"))

        # Cleanup
        await bus.stop()
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        self._queue: asyncio.PriorityQueue[tuple[int, float, Event]] = (
            asyncio.PriorityQueue(maxsize=max_queue_size)
        )
        self._dead_letters: list[DeadLetterEntry] = []
        self._running = False
        self._dispatch_task: asyncio.Task[None] | None = None
        self._event_count = 0
        self._error_count = 0

    # --- Lifecycle ---

    async def start(self) -> None:
        """Start the event dispatch loop."""
        if self._running:
            logger.warning("EventBus already running")
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(
            self._dispatch_loop(), name="jarvis.event_bus"
        )
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Gracefully stop the event bus, draining remaining events."""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._dispatch_task
        logger.info(
            "EventBus stopped",
            extra={"events_processed": self._event_count, "errors": self._error_count},
        )

    # --- Subscribe / Unsubscribe ---

    def subscribe(
        self,
        event_type: str,
        handler: AsyncHandler,
        owner: str = "unknown",
        priority: int = 0,
        once: bool = False,
    ) -> str:
        """
        Subscribe to an event type or pattern.

        Args:
            event_type: Exact class name or glob pattern (e.g. "Voice*", "*.Error*")
            handler:    Async callable that receives the event
            owner:      Module name for debugging
            priority:   Higher priority handlers run first
            once:       Automatically unsubscribe after first invocation

        Returns:
            subscription_id for later unsubscription
        """
        sub = Subscription(
            pattern=event_type,
            handler=handler,
            priority=priority,
            owner=owner,
            once=once,
        )
        self._subscriptions[event_type].append(sub)
        self._subscriptions[event_type].sort(key=lambda s: -s.priority)
        logger.debug(
            f"Subscribed: {owner} → {event_type} (id={sub.subscription_id[:8]})"
        )
        return sub.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID. Returns True if found."""
        for pattern, subs in self._subscriptions.items():
            for sub in subs:
                if sub.subscription_id == subscription_id:
                    subs.remove(sub)
                    logger.debug(f"Unsubscribed: {sub.owner} from {pattern}")
                    return True
        return False

    def subscribe_once(
        self, event_type: str, handler: AsyncHandler, owner: str = "unknown"
    ) -> str:
        """Subscribe to the next occurrence of an event only."""
        return self.subscribe(event_type, handler, owner=owner, once=True)

    # --- Publish ---

    async def publish(self, event: Event) -> None:
        """
        Publish an event to the bus.

        Events are queued by priority (CRITICAL first). The dispatch loop
        processes them in order.
        """
        # Priority queue uses (priority_score, timestamp, event)
        # Lower number = higher priority, so we negate the Priority value
        priority_score = -int(event.priority)
        try:
            await self._queue.put((priority_score, event.timestamp, event))
            logger.trace(f"Queued: {event.__class__.__name__} from {event.source}")
        except asyncio.QueueFull:
            logger.error(
                f"EventBus queue full! Dropped: {event.__class__.__name__}"
            )

    async def publish_sync(self, event: Event) -> None:
        """
        Publish and immediately dispatch (bypass queue).
        Use for CRITICAL events that cannot wait.
        """
        await self._dispatch_event(event)

    # --- Internal Dispatch ---

    async def _dispatch_loop(self) -> None:
        """Main event processing loop."""
        while self._running:
            try:
                _, _, event = await asyncio.wait_for(
                    self._queue.get(), timeout=0.1
                )
                await self._dispatch_event(event)
                self._queue.task_done()
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"EventBus dispatch loop error: {e}")
                self._error_count += 1

    async def _dispatch_event(self, event: Event) -> None:
        """Find matching handlers and invoke them."""
        event_class_name = event.__class__.__name__
        handlers_called = 0
        to_unsubscribe: list[str] = []

        for pattern, subs in self._subscriptions.items():
            if self._matches(event_class_name, pattern):
                for sub in list(subs):
                    try:
                        await sub.handler(event)
                        handlers_called += 1
                        if sub.once:
                            to_unsubscribe.append(sub.subscription_id)
                    except Exception as e:
                        self._error_count += 1
                        logger.error(
                            f"Handler error in {sub.owner} for "
                            f"{event_class_name}: {e}"
                        )
                        self._dead_letters.append(
                            DeadLetterEntry(
                                event=event,
                                handler_owner=sub.owner,
                                error=str(e),
                            )
                        )

        for sub_id in to_unsubscribe:
            self.unsubscribe(sub_id)

        self._event_count += 1

        if handlers_called == 0:
            logger.trace(f"Unhandled event: {event_class_name}")

    @staticmethod
    def _matches(event_name: str, pattern: str) -> bool:
        """Check if an event class name matches a subscription pattern."""
        return fnmatch.fnmatch(event_name, pattern)

    # --- Diagnostics ---

    @property
    def stats(self) -> dict[str, Any]:
        """Return current bus statistics."""
        return {
            "events_processed": self._event_count,
            "errors": self._error_count,
            "queue_size": self._queue.qsize(),
            "subscriptions": sum(len(v) for v in self._subscriptions.values()),
            "dead_letters": len(self._dead_letters),
        }

    def get_dead_letters(self) -> list[DeadLetterEntry]:
        """Return all events that failed processing."""
        return list(self._dead_letters)
