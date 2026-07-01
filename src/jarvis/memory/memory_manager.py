"""
Memory Manager
==============
Orchestrates JARVIS's memory layers behind a single interface:

  - Working memory  — fast, bounded, in-process (:class:`ShortTermMemory`)
  - Episodic memory — persistent conversation history (SQLite via
    :class:`ConversationHistory`)

Semantic (vector) memory is intentionally not wired here yet — it depends on
the heavy ``lancedb`` + ``fastembed`` stack. ``MemoryManager`` degrades
gracefully if persistent storage is unavailable, keeping working memory live.

Usage:
    mem = MemoryManager(settings)
    await mem.initialize(title="CLI chat")
    await mem.add_exchange("Hello", "Hi, I'm JARVIS.")
    history = mem.recent_messages()      # list[Message] for the LLM
    await mem.close()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from jarvis.ai.providers.base import Message, Role
from jarvis.memory.conversation_history import ConversationHistory
from jarvis.memory.short_term import MemoryEntry, ShortTermMemory

if TYPE_CHECKING:
    from jarvis.config.settings import Settings

__all__ = ["MemoryManager"]


class MemoryManager:
    """
    Unified front door to JARVIS's memory layers.

    Working memory is always available. Persistent history is enabled by
    ``initialize()`` and silently skipped if its backend (``aiosqlite``) is
    not installed.

    Usage:
        mem = MemoryManager(db_path="data/memory/long_term/conversations.db")
        await mem.initialize()
        await mem.add_exchange(user_text, assistant_text)
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        db_path: str | None = None,
        max_working: int = 50,
    ) -> None:
        self._settings = settings
        self._working = ShortTermMemory(max_entries=max_working)
        resolved_db = db_path or "data/memory/long_term/conversations.db"
        self._history = ConversationHistory(db_path=resolved_db)
        self._session_id: str | None = None
        self._persistent = False

    # --- Lifecycle ---

    async def initialize(self, title: str = "Session") -> None:
        """Open persistent history and start a session (degrades gracefully)."""
        try:
            await self._history.initialize()
            session = await self._history.new_session(title=title)
            self._session_id = session.session_id
            self._persistent = True
            logger.debug("MemoryManager: persistent session {}", self._session_id[:8])
        except ImportError as exc:
            logger.warning(
                "Persistent memory unavailable ({}); using working memory only", exc
            )
            self._persistent = False

    async def close(self) -> None:
        """Flush and close the persistent store."""
        if self._persistent:
            await self._history.close()

    # --- Writes ---

    async def add_exchange(self, user: str, assistant: str) -> None:
        """Record one user/assistant turn in working and persistent memory."""
        self._working.add("user", user)
        self._working.add("assistant", assistant)
        if self._persistent and self._session_id is not None:
            await self._history.add_message(self._session_id, "user", user)
            await self._history.add_message(self._session_id, "assistant", assistant)

    # --- Reads ---

    def recent_messages(self, limit: int | None = None) -> list[Message]:
        """Working-memory turns as :class:`Message` objects for the LLM."""
        messages: list[Message] = []
        for entry in self._working.get_recent(limit):
            try:
                role = Role(entry.role)
            except ValueError:
                role = Role.USER
            messages.append(Message(role=role, content=entry.content))
        return messages

    def build_context_string(self, max_recent: int = 10) -> str:
        """A compact ``role: content`` transcript of recent working memory."""
        return "\n".join(
            f"{entry.role}: {entry.content}"
            for entry in self._working.get_recent(max_recent)
        )

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Keyword search over working memory."""
        return self._working.search(query, max_results=limit)

    # --- Properties ---

    @property
    def working(self) -> ShortTermMemory:
        return self._working

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def is_persistent(self) -> bool:
        return self._persistent
