"""
Audit Logger
============
Immutable append-only log of every action JARVIS takes.
This is the source of truth for what JARVIS has done.

Format: JSONL (one JSON object per line) for easy parsing/ingestion.

Every entry captures:
- timestamp
- action type
- module that performed it
- arguments
- result (success/failure)
- permission level required
- user approval (yes/no/auto)
- session ID

This log should NEVER be deleted or modified — only appended to.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class AuditEntry:
    """A single audit log entry."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    module: str = ""
    action: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    result: str = "success"         # success | failure | denied | error
    error: str = ""
    risk_level: str = "low"
    user_approved: bool | None = None  # None = not required
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """
    Append-only audit log for all JARVIS actions.

    Usage:
        audit = AuditLogger(log_path="data/audit/audit.jsonl")
        await audit.initialize()

        await audit.log(AuditEntry(
            module="desktop.file_system",
            action="read_file",
            args={"path": "~/Documents/report.pdf"},
            risk_level="read_only",
            user_approved=None,  # Not required
        ))
    """

    def __init__(
        self,
        log_path: str = "data/audit/audit.jsonl",
        session_id: str | None = None,
    ) -> None:
        self._log_path = Path(log_path)
        self._session_id = session_id or str(uuid.uuid4())
        self._entry_count = 0

    async def initialize(self) -> None:
        """Set up the audit log file."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        # Log session start
        await self.log(AuditEntry(
            module="core.security",
            action="session_start",
            session_id=self._session_id,
            metadata={"log_path": str(self._log_path)},
        ))
        logger.info(
            f"Audit log initialized: {self._log_path} "
            f"(session={self._session_id[:8]})"
        )

    async def log(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log."""
        entry.session_id = self._session_id

        # Convert to JSON and append (append mode = immutable)
        line = json.dumps(asdict(entry), separators=(",", ":"))
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        self._entry_count += 1

        if entry.result in ("failure", "denied", "error"):
            logger.warning(
                f"Audit [{entry.result.upper()}] {entry.module}.{entry.action}"
            )
        else:
            logger.trace(
                f"Audit [OK] {entry.module}.{entry.action}"
            )

    async def log_action(
        self,
        module: str,
        action: str,
        args: dict[str, Any] | None = None,
        result: str = "success",
        risk_level: str = "low",
        user_approved: bool | None = None,
        error: str = "",
        duration_ms: float = 0.0,
    ) -> None:
        """Convenience method for logging an action."""
        await self.log(AuditEntry(
            module=module,
            action=action,
            args=args or {},
            result=result,
            risk_level=risk_level,
            user_approved=user_approved,
            error=error,
            duration_ms=duration_ms,
        ))

    async def read_entries(
        self,
        limit: int = 100,
        module_filter: str | None = None,
        result_filter: str | None = None,
    ) -> list[AuditEntry]:
        """Read recent audit entries (for display/analysis)."""
        if not self._log_path.exists():
            return []

        entries: list[AuditEntry] = []
        with open(self._log_path, encoding="utf-8") as f:
            lines = f.readlines()

        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if module_filter and not data.get("module", "").startswith(module_filter):
                    continue
                if result_filter and data.get("result") != result_filter:
                    continue
                entries.append(AuditEntry(**data))
                if len(entries) >= limit:
                    break
            except Exception:
                continue

        return entries

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def entry_count(self) -> int:
        return self._entry_count
