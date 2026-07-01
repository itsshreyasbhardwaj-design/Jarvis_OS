"""
Conversation History
====================
Persistent storage of all conversations. Each conversation has a
session ID, title, and a list of messages.

Used for:
- Restoring context from previous sessions
- Searching past conversations
- Training data collection (opt-in)
- Audit trail of AI interactions
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class ConversationSession:
    """A conversation session (one wake-to-sleep cycle or deliberate grouping)."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversationHistory:
    """
    Persistent conversation storage backed by SQLite.

    Usage:
        history = ConversationHistory()
        await history.initialize()

        session = await history.new_session(title="Morning tasks")
        await history.add_message(session.session_id, "user", "Open Chrome")
        await history.add_message(session.session_id, "assistant", "Opening Chrome...")

        sessions = await history.list_sessions(limit=10)
        messages = await history.get_messages(session.session_id)
    """

    def __init__(self, db_path: str = "data/memory/long_term/conversations.db") -> None:
        self._db_path = Path(db_path)
        self._conn: Any = None
        self._current_session_id: str | None = None

    async def initialize(self) -> None:
        """Initialize the conversation history store."""
        import aiosqlite
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self._db_path))
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._create_schema()
        logger.info(f"Conversation history initialized: {self._db_path}")

    async def _create_schema(self) -> None:
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT DEFAULT '',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            )
        """)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )
        await self._conn.commit()

    async def new_session(self, title: str = "") -> ConversationSession:
        """Create a new conversation session."""
        session = ConversationSession(title=title)
        await self._conn.execute(
            """INSERT INTO sessions (session_id, title, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (session.session_id, session.title, session.created_at, session.updated_at),
        )
        await self._conn.commit()
        self._current_session_id = session.session_id
        logger.debug(f"New conversation session: {session.session_id[:8]}")
        return session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to a session."""
        now = time.time()
        await self._conn.execute(
            """INSERT INTO messages (session_id, role, content, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, role, content, now, json.dumps(metadata or {})),
        )
        await self._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (now, session_id),
        )
        await self._conn.commit()

    async def get_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve messages for a session."""
        sql = (  # noqa: E501
            "SELECT role, content, timestamp, metadata"
            " FROM messages WHERE session_id=? ORDER BY timestamp"
        )
        params: list[Any] = [session_id]
        if limit:
            sql += " DESC LIMIT ?"
            params.append(limit)

        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()

        messages = [
            {
                "role": r[0],
                "content": r[1],
                "timestamp": r[2],
                "metadata": json.loads(r[3]),
            }
            for r in rows
        ]
        if limit:
            messages.reverse()
        return messages

    async def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent conversation sessions."""
        cursor = await self._conn.execute(
            """SELECT session_id, title, created_at, updated_at
               FROM sessions ORDER BY updated_at DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {"session_id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
            for r in rows
        ]

    @property
    def current_session_id(self) -> str | None:
        return self._current_session_id

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
