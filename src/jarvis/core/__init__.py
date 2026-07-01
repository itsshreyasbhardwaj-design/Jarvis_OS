"""Core application infrastructure: event bus, DI container, lifecycle."""

from jarvis.core.application import JarvisOS
from jarvis.core.event_bus import Event, EventBus, Priority
from jarvis.core.lifecycle import AppState, LifecycleManager, LifecycleModule
from jarvis.core.service_registry import ServiceRegistry

__all__ = [
    "JarvisOS",
    "EventBus",
    "Event",
    "Priority",
    "LifecycleManager",
    "LifecycleModule",
    "AppState",
    "ServiceRegistry",
]
