"""
Knowledge Store (Vector Database)
===================================
Semantic memory using LanceDB + FastEmbed.

Stack (v2 — June 2026):
- LanceDB: Rust-backed HNSW, hybrid vector+FTS, no server, embedded
  Replaces ChromaDB (LanceDB is faster, no server required, native persistence)
- FastEmbed: ONNX embeddings, 80 MB RAM, no PyTorch dep, fast cold start
  Replaces sentence-transformers as default embedder

Use cases:
- "What did we discuss about Python last week?" (semantic search)
- Finding related tasks, files, or conversations
- Building a personal knowledge graph over time
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class KnowledgeEntry:
    """A semantically indexed knowledge entry."""
    content: str
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    distance: float = 0.0           # Similarity distance (lower = more similar)
    created_at: float = field(default_factory=time.time)


class KnowledgeStore:
    """
    Semantic vector knowledge store backed by LanceDB + FastEmbed.

    Usage:
        store = KnowledgeStore(path="data/memory/vector_store")
        await store.initialize()

        entry_id = await store.add(
            "User works as a software engineer at a startup",
            metadata={"source": "conversation", "importance": 0.8}
        )

        results = await store.search("what does the user do for work?", limit=5)
        for entry in results:
            print(entry.content, entry.distance)
    """

    def __init__(
        self,
        path: str = "data/memory/vector_store",
        table_name: str = "jarvis_knowledge",
        embedding_model: str = "BAAI/bge-small-en-v1.5",  # FastEmbed default — 80MB RAM
    ) -> None:
        self._path = path
        self._table_name = table_name
        self._embedding_model = embedding_model
        self._db: Any = None
        self._table: Any = None
        self._embedder: Any = None

    async def initialize(self) -> None:
        """Connect to LanceDB and set up the table."""
        await asyncio.get_event_loop().run_in_executor(None, self._init_sync)
        logger.info(
            "Knowledge store initialized: {} (model={})",
            self._path,
            self._embedding_model,
        )

    def _init_sync(self) -> None:
        """Blocking init — runs in thread pool."""
        try:
            import lancedb  # type: ignore[import-untyped]
            self._db = lancedb.connect(self._path)

            # Load FastEmbed for ONNX embeddings (no PyTorch, fast cold start)
            try:
                from fastembed import TextEmbedding  # type: ignore[import-untyped]
                self._embedder = TextEmbedding(model_name=self._embedding_model)
                logger.debug("FastEmbed embedder loaded: {}", self._embedding_model)
            except ImportError:
                logger.warning(
                    "fastembed not installed — using LanceDB built-in embeddings. "
                    "Install: pip install fastembed>=0.3.0"
                )
                self._embedder = None

            # Create or open table
            existing = self._db.table_names()
            if self._table_name in existing:
                self._table = self._db.open_table(self._table_name)
                logger.debug(
                    "Opened existing LanceDB table '{}' ({} entries)",
                    self._table_name,
                    self._table.count_rows(),
                )
            else:
                # Table will be created on first add()
                self._table = None
                logger.debug("LanceDB table '{}' will be created on first add", self._table_name)

        except ImportError:
            logger.warning(
                "lancedb not installed — knowledge store disabled. "
                "Install: pip install lancedb>=0.10.0"
            )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using FastEmbed (ONNX, no PyTorch)."""
        if self._embedder is None:
            # Fallback: return zero vectors (knowledge store degraded)
            return [[0.0] * 384 for _ in texts]
        embeddings = list(self._embedder.embed(texts))
        return [e.tolist() for e in embeddings]

    async def add(
        self,
        content: str,
        *,
        entry_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a document to the knowledge store."""
        if self._db is None:
            return ""

        doc_id = entry_id or str(uuid.uuid4())
        meta = {**(metadata or {}), "created_at": time.time()}

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._add_sync(doc_id, content, meta)
        )
        return doc_id

    def _add_sync(self, doc_id: str, content: str, metadata: dict[str, Any]) -> None:
        """Blocking add — runs in thread pool."""
        import pyarrow as pa  # type: ignore[import-untyped]

        vector = self._embed([content])[0]
        row = {
            "id": doc_id,
            "content": content,
            "vector": vector,
            "metadata": str(metadata),
            "created_at": metadata.get("created_at", time.time()),
        }

        if self._table is None:
            # Create table on first insert
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), len(vector))),
                pa.field("metadata", pa.string()),
                pa.field("created_at", pa.float64()),
            ])
            self._table = self._db.create_table(
                self._table_name,
                data=[row],
                schema=schema,
                mode="overwrite",
            )
        else:
            self._table.add([row])

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        min_similarity: float = 0.3,
    ) -> list[KnowledgeEntry]:
        """Semantic search for the most relevant knowledge entries."""
        if self._db is None or self._table is None:
            return []

        results = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._search_sync(query, limit)
        )

        entries = []
        for row in results:
            distance = float(row.get("_distance", 0.0))
            similarity = 1.0 - distance
            if similarity >= min_similarity:
                entries.append(KnowledgeEntry(
                    content=row["content"],
                    entry_id=row["id"],
                    distance=distance,
                    created_at=float(row.get("created_at", 0.0)),
                ))
        return entries

    def _search_sync(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Blocking vector search."""
        vector = self._embed([query])[0]
        results = (
            self._table.search(vector)
            .limit(limit)
            .to_list()
        )
        return results  # type: ignore[return-value]

    async def delete(self, entry_id: str) -> None:
        """Remove an entry from the store."""
        if self._table:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._table.delete(f"id = '{entry_id}'")
            )

    async def count(self) -> int:
        """Return total entries in the store."""
        if not self._table:
            return 0
        return int(self._table.count_rows())
