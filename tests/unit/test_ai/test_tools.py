"""Unit tests for built-in tools (search_web) and result formatting."""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.ai.providers.base import ToolCall
from jarvis.ai.tools import (
    _hardened_file_permissions,
    build_tool_executor,
    format_search_results,
)
from jarvis.desktop.permissions import PermissionManager, PermissionResult
from jarvis.integrations.desktop_control import ControlResult
from jarvis.integrations.web_search import SearchResult


class _FakeDesktop:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def open_app(self, name: str) -> ControlResult:
        self.calls.append(("open_app", name))
        return ControlResult(success=True, output=f"opened {name}")

    async def open_url(self, url: str) -> ControlResult:
        self.calls.append(("open_url", url))
        return ControlResult(success=True, output=f"opened {url}")

    async def run_applescript(self, script: str) -> ControlResult:
        self.calls.append(("applescript", script))
        return ControlResult(success=True, output="scripted")

    async def set_volume(self, level: int) -> ControlResult:
        self.calls.append(("set_volume", level))
        return ControlResult(success=True)

    async def type_text(self, text: str) -> ControlResult:
        self.calls.append(("type_text", text))
        return ControlResult(success=True)

    async def open_smart(self, target: str) -> ControlResult:
        self.calls.append(("open_smart", target))
        return ControlResult(success=True, output=f"opened {target}")

    async def take_screenshot(self) -> ControlResult:
        self.calls.append(("take_screenshot", ""))
        return ControlResult(success=True, output="screenshot saved")

    async def lock_screen(self) -> ControlResult:
        self.calls.append(("lock_screen", ""))
        return ControlResult(success=True, output="screen locked")

    async def media_control(self, action: str) -> ControlResult:
        self.calls.append(("media_control", action))
        return ControlResult(success=True)


class _FakeWebSearch:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        return self._results[:max_results]


def _call(query: str) -> ToolCall:
    return ToolCall(id="1", name="search_web", arguments={"query": query})


@pytest.mark.unit
class TestToolFormatting:
    def test_format_empty(self) -> None:
        assert "nothing" in format_search_results("x", [])

    def test_format_lists_results(self) -> None:
        out = format_search_results(
            "python", [SearchResult(title="Python", url="http://p", snippet="a language")]
        )
        assert "1. Python" in out
        assert "http://p" in out


@pytest.mark.unit
class TestSearchWebTool:
    @pytest.mark.asyncio
    async def test_executes_and_returns_results(self) -> None:
        web = _FakeWebSearch([SearchResult(title="Dune", url="http://d", snippet="a novel")])
        executor = build_tool_executor(web_search=web)
        results = await executor.execute_all([_call("dune")])
        assert results[0].success
        assert "Dune" in results[0].output

    @pytest.mark.asyncio
    async def test_low_risk_allowed_even_in_safe_mode(self) -> None:
        web = _FakeWebSearch([SearchResult(title="OK", url="", snippet="")])
        executor = build_tool_executor(
            web_search=web, permissions=PermissionManager(safe_mode=True)
        )
        results = await executor.execute_all([_call("q")])
        assert results[0].success
        assert "OK" in results[0].output

    @pytest.mark.asyncio
    async def test_permission_denied_returns_denial(self) -> None:
        class _DenyPerms:
            async def check(self, _request) -> PermissionResult:
                return PermissionResult(granted=False, reason="not allowed")

        web = _FakeWebSearch([SearchResult(title="secret", url="", snippet="")])
        executor = build_tool_executor(web_search=web, permissions=_DenyPerms())
        results = await executor.execute_all([_call("x")])
        assert results[0].success  # handler ran cleanly
        assert "Permission denied" in results[0].output


def _executor():
    return build_tool_executor(web_search=_FakeWebSearch([]))


@pytest.mark.unit
class TestFileSystemTimeTools:
    @pytest.mark.asyncio
    async def test_list_directory(self, tmp_path) -> None:
        (tmp_path / "note.txt").write_text("hi")
        (tmp_path / "sub").mkdir()
        results = await _executor().execute_all(
            [ToolCall(id="1", name="list_directory", arguments={"path": str(tmp_path)})]
        )
        assert results[0].success
        assert "note.txt" in results[0].output
        assert "sub/" in results[0].output

    @pytest.mark.asyncio
    async def test_read_file(self, tmp_path) -> None:
        target = tmp_path / "note.txt"
        target.write_text("hello jarvis")
        results = await _executor().execute_all(
            [ToolCall(id="1", name="read_file", arguments={"path": str(target)})]
        )
        assert results[0].success
        assert "hello jarvis" in results[0].output

    @pytest.mark.asyncio
    async def test_read_missing_file_is_friendly(self, tmp_path) -> None:
        results = await _executor().execute_all(
            [ToolCall(id="1", name="read_file", arguments={"path": str(tmp_path / "nope.txt")})]
        )
        assert results[0].success  # returns a message rather than raising
        assert "Could not read" in results[0].output

    def test_hardened_permissions_block_credentials(self) -> None:
        pm = _hardened_file_permissions()
        assert pm.check_path(str(Path.home() / ".ssh" / "id_rsa")) is False
        assert pm.check_path(str(Path.home() / ".aws" / "credentials")) is False

    @pytest.mark.asyncio
    async def test_system_status(self) -> None:
        results = await _executor().execute_all(
            [ToolCall(id="1", name="system_status", arguments={})]
        )
        assert results[0].success
        assert "CPU" in results[0].output
        assert "Disk" in results[0].output

    @pytest.mark.asyncio
    async def test_get_time(self) -> None:
        results = await _executor().execute_all(
            [ToolCall(id="1", name="get_time", arguments={})]
        )
        assert results[0].success
        assert "It is" in results[0].output


@pytest.mark.unit
class TestDesktopControlTools:
    @pytest.mark.asyncio
    async def test_open_app_tool(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="open_app", arguments={"name": "Safari"})]
        )
        assert results[0].success
        assert ("open_app", "Safari") in desk.calls

    @pytest.mark.asyncio
    async def test_open_url_tool(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="open_url", arguments={"url": "apple.com"})]
        )
        assert results[0].success
        assert ("open_url", "apple.com") in desk.calls

    @pytest.mark.asyncio
    async def test_control_mac_tool_runs_live_applescript(self) -> None:
        # Real osascript, benign and deterministic.
        executor = build_tool_executor(web_search=_FakeWebSearch([]))
        results = await executor.execute_all(
            [ToolCall(id="1", name="control_mac", arguments={"script": 'return "ok"'})]
        )
        assert results[0].success
        assert "ok" in results[0].output

    @pytest.mark.asyncio
    async def test_set_volume_tool_parses_level(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="set_volume", arguments={"level": "30"})]
        )
        assert results[0].success
        assert ("set_volume", 30) in desk.calls

    @pytest.mark.asyncio
    async def test_type_text_tool(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="type_text", arguments={"text": "hello world"})]
        )
        assert results[0].success
        assert ("type_text", "hello world") in desk.calls

    @pytest.mark.asyncio
    async def test_open_thing_tool(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="open_thing", arguments={"target": "Downloads"})]
        )
        assert results[0].success
        assert ("open_smart", "Downloads") in desk.calls

    @pytest.mark.asyncio
    async def test_take_screenshot_tool(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="take_screenshot", arguments={})]
        )
        assert results[0].success
        assert ("take_screenshot", "") in desk.calls

    @pytest.mark.asyncio
    async def test_lock_screen_tool(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="lock_screen", arguments={})]
        )
        assert results[0].success
        assert ("lock_screen", "") in desk.calls

    @pytest.mark.asyncio
    async def test_media_control_tool(self) -> None:
        desk = _FakeDesktop()
        executor = build_tool_executor(web_search=_FakeWebSearch([]), desktop=desk)
        results = await executor.execute_all(
            [ToolCall(id="1", name="media_control", arguments={"action": "pause"})]
        )
        assert results[0].success
        assert ("media_control", "pause") in desk.calls
