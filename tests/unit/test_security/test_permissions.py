"""Unit tests for the permission system."""

from __future__ import annotations

import pytest

from jarvis.desktop.permissions import (
    PermissionManager,
    PermissionRequest,
    RiskLevel,
)


@pytest.mark.unit
class TestPermissionManager:

    @pytest.mark.asyncio
    async def test_read_only_always_permitted(
        self, restricted_permissions: PermissionManager
    ) -> None:
        result = await restricted_permissions.check(PermissionRequest(
            action_name="read_file",
            risk_level=RiskLevel.READ_ONLY,
            description="Read a file",
        ))
        assert result.granted is True

    @pytest.mark.asyncio
    async def test_high_risk_blocked_in_safe_mode(
        self, restricted_permissions: PermissionManager
    ) -> None:
        result = await restricted_permissions.check(PermissionRequest(
            action_name="delete_file",
            risk_level=RiskLevel.HIGH,
            description="Delete a file",
        ))
        assert result.granted is False
        assert "safe" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_low_risk_always_permitted(
        self, permissive_permissions: PermissionManager
    ) -> None:
        result = await permissive_permissions.check(PermissionRequest(
            action_name="open_app",
            risk_level=RiskLevel.LOW,
            description="Open Chrome",
        ))
        assert result.granted is True

    def test_forbidden_path_blocked(
        self, restricted_permissions: PermissionManager
    ) -> None:
        allowed = restricted_permissions.check_path("/System/Library/CoreServices")
        assert allowed is False

    def test_normal_path_allowed_when_no_allowlist(self) -> None:
        pm = PermissionManager(
            require_confirmation=False,
            safe_mode=False,
            allowed_paths=[],
            forbidden_paths=["/System"],
        )
        assert pm.check_path("/Users/test/Documents/file.txt") is True

    @pytest.mark.asyncio
    async def test_action_history_recorded(
        self, permissive_permissions: PermissionManager
    ) -> None:
        await permissive_permissions.check(PermissionRequest(
            action_name="test_action",
            risk_level=RiskLevel.LOW,
            description="Test",
        ))
        history = permissive_permissions.get_history()
        assert len(history) == 1
        assert history[0]["action"] == "test_action"
