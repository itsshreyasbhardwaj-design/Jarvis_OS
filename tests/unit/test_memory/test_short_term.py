"""Unit tests for short-term memory."""

from __future__ import annotations

import pytest

from jarvis.memory.short_term import ShortTermMemory


@pytest.mark.unit
class TestShortTermMemory:

    def test_add_and_retrieve(self) -> None:
        mem = ShortTermMemory(max_entries=5)
        mem.add("user", "Hello JARVIS")
        entries = mem.get_recent()
        assert len(entries) == 1
        assert entries[0].content == "Hello JARVIS"
        assert entries[0].role == "user"

    def test_fifo_eviction_when_full(self) -> None:
        mem = ShortTermMemory(max_entries=3)
        mem.add("user", "message 1")
        mem.add("assistant", "response 1")
        mem.add("user", "message 2")
        mem.add("assistant", "response 2")  # Should evict message 1

        assert len(mem) == 3
        entries = mem.get_recent()
        assert entries[0].content == "response 1"  # message 1 evicted

    def test_get_recent_limit(self) -> None:
        mem = ShortTermMemory(max_entries=10)
        for i in range(7):
            mem.add("user", f"message {i}")

        recent = mem.get_recent(3)
        assert len(recent) == 3
        assert recent[-1].content == "message 6"

    def test_clear(self) -> None:
        mem = ShortTermMemory()
        mem.add("user", "test")
        mem.clear()
        assert len(mem) == 0

    def test_search(self) -> None:
        mem = ShortTermMemory()
        mem.add("user", "open the terminal")
        mem.add("assistant", "Opening terminal...")
        mem.add("user", "search for python files")

        results = mem.search("terminal")
        assert len(results) == 2

    def test_is_full(self) -> None:
        mem = ShortTermMemory(max_entries=2)
        assert not mem.is_full
        mem.add("user", "a")
        mem.add("user", "b")
        assert mem.is_full
