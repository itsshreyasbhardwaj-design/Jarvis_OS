"""Unit tests for the JARVIS EventBus."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from jarvis.core.event_bus import Event, EventBus, Priority


@dataclass
class TestEvent(Event):
    message: str = ""
    source: str = "test"


@dataclass
class AnotherEvent(Event):
    value: int = 0
    source: str = "test"


@pytest.mark.unit
class TestEventBus:
    """Test suite for EventBus."""

    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self, event_bus: EventBus) -> None:
        """Handler receives published events."""
        received: list[TestEvent] = []

        async def handler(event: TestEvent) -> None:
            received.append(event)

        event_bus.subscribe("TestEvent", handler, owner="test")
        await event_bus.publish(TestEvent(message="hello"))
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0].message == "hello"

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus: EventBus) -> None:
        """Wildcard patterns match multiple event types."""
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        event_bus.subscribe("Test*", handler, owner="test")
        await event_bus.publish(TestEvent(message="a"))
        await event_bus.publish(AnotherEvent(value=1))
        await asyncio.sleep(0.05)

        # Only TestEvent matches "Test*"
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_subscribe_once(self, event_bus: EventBus) -> None:
        """subscribe_once handler fires only for the first event."""
        received: list[TestEvent] = []

        async def handler(event: TestEvent) -> None:
            received.append(event)

        event_bus.subscribe_once("TestEvent", handler, owner="test")
        await event_bus.publish(TestEvent(message="first"))
        await event_bus.publish(TestEvent(message="second"))
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].message == "first"

    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus: EventBus) -> None:
        """Unsubscribing prevents future delivery."""
        received: list[TestEvent] = []

        async def handler(event: TestEvent) -> None:
            received.append(event)

        sub_id = event_bus.subscribe("TestEvent", handler, owner="test")
        await event_bus.publish(TestEvent(message="before"))
        await asyncio.sleep(0.05)

        event_bus.unsubscribe(sub_id)
        await event_bus.publish(TestEvent(message="after"))
        await asyncio.sleep(0.05)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_handler_error_does_not_crash_bus(
        self, event_bus: EventBus
    ) -> None:
        """A crashing handler is caught and logged, bus continues."""
        async def bad_handler(event: TestEvent) -> None:
            raise ValueError("Intentional test error")

        good_received: list[TestEvent] = []

        async def good_handler(event: TestEvent) -> None:
            good_received.append(event)

        event_bus.subscribe("TestEvent", bad_handler, owner="bad")
        event_bus.subscribe("TestEvent", good_handler, owner="good")

        await event_bus.publish(TestEvent(message="test"))
        await asyncio.sleep(0.1)

        # Good handler still receives the event
        assert len(good_received) == 1
        assert event_bus.stats["errors"] == 1

    def test_stats(self, event_bus: EventBus) -> None:
        """Stats are tracked correctly."""
        stats = event_bus.stats
        assert "events_processed" in stats
        assert "errors" in stats
        assert "queue_size" in stats
