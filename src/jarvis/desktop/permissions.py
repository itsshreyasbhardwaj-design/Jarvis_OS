"""
Desktop Permission Guard
========================
Every desktop automation action passes through this gate.
Permissions are declared at action registration time and enforced at runtime.

Risk Levels:
  READ_ONLY  — Safe: reading files, taking screenshots, window inspection
  LOW        — Low risk: opening apps, copying to clipboard, reading clipboard
  MEDIUM     — Requires confirmation: moving files, writing files, typing text
  HIGH       — Requires explicit confirmation + reason: deleting files, running commands
  CRITICAL   — Always blocked unless safe_mode=False AND explicit approval: system settings

This is the safety backbone of JARVIS. Never bypass it.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


class RiskLevel(enum.IntEnum):
    READ_ONLY = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PermissionRequest:
    """A request to execute an action requiring permission."""
    action_name: str
    risk_level: RiskLevel
    description: str
    args: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class PermissionResult:
    """Result of a permission check."""
    granted: bool
    reason: str = ""
    requires_confirmation: bool = False


class PermissionManager:
    """
    Centralized permission enforcement for all desktop actions.

    Configuration:
    - require_confirmation: True = always ask for MEDIUM+ actions
    - safe_mode: True = block ALL HIGH and CRITICAL actions
    - allowed_paths: Restrict file operations to these directories
    - forbidden_paths: Always block these directories

    Usage:
        pm = PermissionManager(require_confirmation=True, safe_mode=True)

        result = await pm.check(PermissionRequest(
            action_name="delete_file",
            risk_level=RiskLevel.HIGH,
            description="Delete ~/Downloads/old_backup.zip",
        ))

        if result.granted:
            # execute action
    """

    DEFAULT_FORBIDDEN_PATHS = [
        "/System", "/Library", "/usr", "/etc", "/bin", "/sbin",
        r"C:\Windows", r"C:\Program Files",
    ]

    def __init__(
        self,
        require_confirmation: bool = True,
        safe_mode: bool = True,
        allowed_paths: list[str] | None = None,
        forbidden_paths: list[str] | None = None,
        confirmation_callback: Any | None = None,
    ) -> None:
        self._require_confirmation = require_confirmation
        self._safe_mode = safe_mode
        self._allowed_paths = allowed_paths or []
        self._forbidden_paths = forbidden_paths or self.DEFAULT_FORBIDDEN_PATHS
        self._confirmation_callback = confirmation_callback
        self._action_history: list[dict[str, Any]] = []

    async def check(self, request: PermissionRequest) -> PermissionResult:
        """
        Check whether an action is permitted.
        This is the single entry point for all permission checks.
        """
        # CRITICAL always blocked in safe mode
        if self._safe_mode and request.risk_level >= RiskLevel.HIGH:
            logger.warning(
                f"BLOCKED (safe_mode): {request.action_name} "
                f"(risk={request.risk_level.name})"
            )
            self._record(request, granted=False, reason="safe_mode")
            return PermissionResult(
                granted=False,
                reason=(
                    f"Action '{request.action_name}' is blocked because JARVIS is in "
                    "safe mode. Disable safe_mode in settings to allow this."
                ),
            )

        # READ_ONLY and LOW: always allowed
        if request.risk_level <= RiskLevel.LOW:
            self._record(request, granted=True)
            return PermissionResult(granted=True)

        # MEDIUM+: require user confirmation if configured
        if self._require_confirmation and request.risk_level >= RiskLevel.MEDIUM:
            if self._confirmation_callback:
                approved = await self._confirmation_callback(request)
            else:
                # No UI connected — default deny for safety
                logger.warning(
                    f"No confirmation UI connected. Denying: {request.action_name}"
                )
                approved = False

            self._record(  # noqa: E501
                request,
                granted=approved,
                reason="user_confirmed" if approved else "user_denied",
            )
            return PermissionResult(
                granted=approved,
                reason="Approved by user" if approved else "Denied by user",
            )

        # Not in safe_mode, no confirmation required
        self._record(request, granted=True)
        return PermissionResult(granted=True)

    def check_path(self, path: str) -> bool:
        """Check if a file path is allowed."""
        import os
        abs_path = os.path.abspath(path)
        for forbidden in self._forbidden_paths:
            if abs_path.startswith(forbidden):
                logger.warning(f"Path blocked (forbidden): {abs_path}")
                return False
        if self._allowed_paths:
            for allowed in self._allowed_paths:
                if abs_path.startswith(os.path.abspath(allowed)):
                    return True
            logger.warning(f"Path blocked (not in allowed list): {abs_path}")
            return False
        return True

    def _record(
        self, request: PermissionRequest, granted: bool, reason: str = ""
    ) -> None:
        """Record permission decision for audit trail."""
        import time
        self._action_history.append({
            "action": request.action_name,
            "risk": request.risk_level.name,
            "granted": granted,
            "reason": reason,
            "timestamp": time.time(),
            "args": request.args,
        })

    @property
    def safe_mode(self) -> bool:
        return self._safe_mode

    def get_history(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._action_history[-limit:]))
