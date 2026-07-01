"""
Long-Term Memory (SQLite-backed)
=================================
Persistent memory that survives restarts. Stores important facts,
completed tasks, learned preferences, and conversation summaries.

Schema:
  memories table:
    id, content, summary, source, importance, created_at, accessed_at,
    access_count, tags, embedding_id, metadata

Retrieval:
  - By recency (most recent first)
  - By importance score (user-defined or AI-scored)
  - By semantic similarity (via vector store integration)
  - By tags
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class LongTermEntry:
    """A persisted long-term memory entry."""
    id: int = 0
    content: str = ""
    summary: str = ""              # AI-generated summary (shorter version)
    source: str = "conversation"   # conversation | task | preference | fact
    importance: float = 0.5        # 0.0–1.0
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding_id: str | None = None  # ChromaDB document ID


class LongTermMemory:
    """
    Persistent memory store backed by SQLite.

    Usage:
        mem = LongTermMemory(db_path="data/memory/long_term/jarvis.db")
        await mem.initialize()

        entry_id = await mem.store(
            content="User prefers dark mode",
            source="preference",
            importance=0.8,
            tags=["ui", "preference"],
        )

        results = await mem.search("dark mode", limit=5)
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str = "data/memory/long_term/jarvis.db") -> None:
        self._db_path = Path(db_path)
        self._conn: Any = None

    async def initialize(self) -> None:
        """Create database and tables."""
        import aiosqlite
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self._db_path))
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._create_schema()
        logger.info(f"Long-term memory initialized: {self._db_path}")

    async def _create_schema(self) -> None:
        """Create database tables if they don't exist."""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                summary TEXT DEFAULT '',
                source TEXT DEFAULT 'conversation',
                importance REAL DEFAULT 0.5,
                tags TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                accessed_at REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                embedding_id TEXT
            )
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_importance
            ON memories(importance DESC)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_source
            ON memories(source)
        """)
        await self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, summary, tags, content=memories, content_rowid=id)
        """)
        await self._conn.commit()

    async def store(
        self,
        content: str,
        *,
        summary: str = "",
        source: str = "conversation",
        importance: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Store a new memory. Returns the entry ID."""
        now = time.time()
        cursor = await self._conn.execute(
            """
            INSERT INTO memories
                (content, summary, source, importance, tags, created_at,
                 accessed_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content,
                summary,
                source,
                importance,
                json.dumps(tags or []),
                now,
                now,
                json.dumps(metadata or {}),
            ),
        )
        await self._conn.commit()
        entry_id = cursor.lastrowid or 0
        logger.debug(
            f"LTM stored: id={entry_id}, source={source}, "
            f"importance={importance:.2f}"
        )
        return entry_id

    async def search(
        self,
        query: str,
        *,
        source: str | None = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> list[LongTermEntry]:
        """Full-text search over memory content."""
        sql = """
            SELECT m.* FROM memories m
            JOIN memories_fts f ON m.id = f.rowid
            WHERE memories_fts MATCH ?
            AND m.importance >= ?
        """
        params: list[Any] = [query, min_importance]

        if source:
            sql += " AND m.source = ?"
            params.append(source)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()

        # Update access count for retrieved entries
        ids = [row[0] for row in rows]
        if ids:
            await self._conn.execute(
                f"UPDATE memories SET accessed_at=?, access_count=access_count+1 "
                f"WHERE id IN ({','.join('?' * len(ids))})",
                [time.time(), *ids],
            )
            await self._conn.commit()

        return [self._row_to_entry(row) for row in rows]

    async def get_recent(self, limit: int = 20) -> list[LongTermEntry]:
        """Retrieve most recently created memories."""
        cursor = await self._conn.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    async def get_important(
        self, min_importance: float = 0.7, limit: int = 20
    ) -> list[LongTermEntry]:
        """Retrieve highest-importance memories."""
        cursor = await self._conn.execute(
            "SELECT * FROM memories WHERE importance >= ? ORDER BY importance DESC LIMIT ?",
            (min_importance, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    async def delete(self, entry_id: int) -> None:
        """Delete a memory entry."""
        await self._conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
        await self._conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def stats(self) -> dict[str, Any]:
        """Return memory statistics."""
        cursor = await self._conn.execute(
            "SELECT COUNT(*), AVG(importance), MAX(created_at) FROM memories"
        )
        row = await cursor.fetchone()
        return {
            "total_entries": row[0] if row else 0,
            "avg_importance": round(row[1] or 0, 3),
            "newest_entry": row[2],
        }

    def _row_to_entry(self, row: tuple) -> LongTermEntry:
        return LongTermEntry(
            id=row[0],
            content=row[1],
            summary=row[2],
            source=row[3],
            importance=row[4],
            tags=json.loads(row[5]),
            created_at=row[6],
            accessed_at=row[7],
            access_count=row[8],
            metadata=json.loads(row[9]),
            embedding_id=row[10],
        )
