"""
Short-Term Memory
=================
In-memory conversation buffer for the current session.
Holds the last N messages and clears on restart.

This is the "working memory" — fast, ephemeral, bounded.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class MemoryEntry:
    """A single item in short-term memory."""
    role: str                          # user | assistant | system | tool
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    entry_id: str = field(default_factory=lambda: str(int(time.time() * 1000)))


class ShortTermMemory:
    """
    Bounded in-memory conversation buffer (FIFO when full).

    Usage:
        mem = ShortTermMemory(max_entries=50)
        mem.add("user", "What files are on my desktop?")
        mem.add("assistant", "Here are the files: ...")

        for entry in mem.get_recent(10):
            print(entry.role, entry.content[:50])
    """

    def __init__(self, max_entries: int = 50) -> None:
        self._buffer: deque[MemoryEntry] = deque(maxlen=max_entries)
        self._max_entries = max_entries

    def add(
        self,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MemoryEntry:
        """Add an entry to short-term memory."""
        entry = MemoryEntry(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self._buffer.append(entry)
        logger.trace(f"STM: +{role} ({len(content)} chars)")
        return entry

    def get_recent(self, n: int | None = None) -> list[MemoryEntry]:
        """Return the last N entries (or all if N is None)."""
        entries = list(self._buffer)
        if n is not None:
            return entries[-n:]
        return entries

    def clear(self) -> None:
        """Clear all short-term memory."""
        count = len(self._buffer)
        self._buffer.clear()
        logger.debug(f"Short-term memory cleared: {count} entries removed")

    def search(self, query: str, max_results: int = 5) -> list[MemoryEntry]:
        """Simple keyword search over recent memory."""
        query_lower = query.lower()
        results = [
            e for e in self._buffer
            if query_lower in e.content.lower()
        ]
        return results[-max_results:]

    def __len__(self) -> int:
        return len(self._buffer)

    def __iter__(self) -> Iterator[MemoryEntry]:
        return iter(self._buffer)

    @property
    def is_full(self) -> bool:
        return len(self._buffer) >= self._max_entries

    @property
    def max_entries(self) -> int:
        return self._max_entries
