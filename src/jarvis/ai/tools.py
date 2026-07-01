"""
Built-in Tools
==============
Registers JARVIS's built-in tools onto a :class:`ToolExecutor`. File access is
routed through a hardened :class:`PermissionManager` (the standard forbidden
system paths *plus* the user's credential directories), so a "read file" tool
can never wander into ``~/.ssh`` or ``~/.aws``.

Tools provided:
  - ``search_web``      keyless DuckDuckGo → Wikipedia search
  - ``list_directory``  list a directory's contents
  - ``read_file``       read a (size-capped) text file
  - ``system_status``   CPU / memory / disk via psutil
  - ``get_time``        current local date and time

Usage:
    executor = build_tool_executor(web_search=WebSearch())
    results = await executor.execute_all([ToolCall(id="1", name="get_time", arguments={})])
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jarvis.ai.tool_executor import ToolExecutor
from jarvis.desktop.file_system.navigator import FileNavigator
from jarvis.desktop.permissions import PermissionManager, PermissionRequest, RiskLevel
from jarvis.integrations.desktop_control import DesktopControl

if TYPE_CHECKING:
    from jarvis.desktop.file_system.navigator import FileInfo
    from jarvis.integrations.web_search import SearchResult, WebSearch

__all__ = ["build_tool_executor", "format_file_list", "format_search_results"]

# Credential directories that file tools must never read, on top of the
# PermissionManager's default system paths.
_SENSITIVE_DIRS = (".ssh", ".aws", ".gnupg", ".config/gcloud")


def _hardened_file_permissions() -> PermissionManager:
    forbidden = list(PermissionManager.DEFAULT_FORBIDDEN_PATHS)
    forbidden += [str(Path.home() / d) for d in _SENSITIVE_DIRS]
    return PermissionManager(
        safe_mode=False, require_confirmation=False, forbidden_paths=forbidden
    )


def _human_size(num_bytes: int) -> str:
    kb = num_bytes / 1024
    if kb < 1:
        return f"{num_bytes} B"
    if kb < 1024:
        return f"{kb:.0f} KB"
    return f"{kb / 1024:.1f} MB"


def format_search_results(query: str, results: list[SearchResult]) -> str:
    """Render search results as a readable, speakable summary."""
    if not results:
        return f'I searched for "{query}" but found nothing useful.'
    lines = [f'Here is what I found for "{query}":']
    for i, result in enumerate(results, start=1):
        line = f"{i}. {result.title}"
        if result.snippet and result.snippet != result.title:
            line += f" — {result.snippet}"
        if result.url:
            line += f" ({result.url})"
        lines.append(line)
    return "\n".join(lines)


def format_file_list(path: str, entries: list[FileInfo]) -> str:
    """Render a directory listing as a readable summary."""
    if not entries:
        return f"{path} is empty (or has no visible files)."
    lines = [f"{path} contains {len(entries)} item(s):"]
    for entry in entries:
        if entry.is_dir:
            lines.append(f"  [dir]  {entry.name}/")
        else:
            lines.append(f"  [file] {entry.name} ({_human_size(entry.size_bytes)})")
    return "\n".join(lines)


async def _system_status() -> str:
    import psutil

    def _collect() -> tuple[float, object, object]:
        return (
            psutil.cpu_percent(interval=0.1),
            psutil.virtual_memory(),
            psutil.disk_usage("/"),
        )

    cpu, mem, disk = await asyncio.to_thread(_collect)
    return (
        f"System status: CPU {cpu:.0f}% | "
        f"RAM {mem.percent:.0f}% used ({mem.used / 1e9:.1f}/{mem.total / 1e9:.1f} GB) | "
        f"Disk {disk.percent:.0f}% used, {disk.free / 1e9:.0f} GB free"
    )


def build_tool_executor(
    *,
    web_search: WebSearch,
    permissions: PermissionManager | None = None,
    desktop: DesktopControl | None = None,
) -> ToolExecutor:
    """Create a ToolExecutor with JARVIS's built-in tools registered."""
    executor = ToolExecutor()
    navigator = FileNavigator(_hardened_file_permissions())
    desktop = desktop or DesktopControl()

    async def _gate(action: str, risk: RiskLevel, description: str) -> str | None:
        if permissions is None:
            return None
        decision = await permissions.check(
            PermissionRequest(action_name=action, risk_level=risk, description=description)
        )
        return None if decision.granted else f"Permission denied: {decision.reason}"

    @executor.register(
        name="search_web",
        description="Search the web for current information using DuckDuckGo and Wikipedia.",
        parameters={"query": {"type": "string", "description": "The search query"}},
        required=["query"],
        risk_level="low",
    )
    async def search_web(query: str) -> str:
        if permissions is not None:
            decision = await permissions.check(
                PermissionRequest(
                    action_name="search_web",
                    risk_level=RiskLevel.LOW,
                    description=f"Web search: {query}",
                )
            )
            if not decision.granted:
                return f"Permission denied: {decision.reason}"
        results = await web_search.search(query, max_results=3)
        return format_search_results(query, results)

    @executor.register(
        name="list_directory",
        description="List the files and folders in a directory.",
        parameters={"path": {"type": "string", "description": "Directory path"}},
        required=["path"],
        risk_level="low",
    )
    async def list_directory(path: str) -> str:
        try:
            entries = await navigator.list_directory(path, limit=50)
        except (PermissionError, NotADirectoryError, FileNotFoundError, OSError) as exc:
            return f"Could not list {path}: {exc}"
        return format_file_list(path, entries)

    @executor.register(
        name="read_file",
        description="Read the contents of a text file.",
        parameters={"path": {"type": "string", "description": "File path"}},
        required=["path"],
        risk_level="low",
    )
    async def read_file(path: str) -> str:
        try:
            content = await navigator.read_text_file(path, max_chars=4000)
        except (PermissionError, FileNotFoundError, ValueError, OSError) as exc:
            return f"Could not read {path}: {exc}"
        return f"Contents of {path}:\n{content}"

    @executor.register(
        name="system_status",
        description="Report current CPU, memory, and disk usage.",
        parameters={},
        risk_level="read_only",
    )
    async def system_status() -> str:
        try:
            return await _system_status()
        except ImportError:
            return "System status is unavailable (psutil is not installed)."

    @executor.register(
        name="get_time",
        description="Get the current local date and time.",
        parameters={},
        risk_level="read_only",
    )
    async def get_time() -> str:
        now = datetime.now(UTC).astimezone()
        return f"It is {now.strftime('%A, %B %d, %Y at %I:%M %p %Z')}."

    @executor.register(
        name="open_app",
        description="Open or focus a macOS application by name (e.g. Safari, Notes, Spotify).",
        parameters={"name": {"type": "string", "description": "Application name"}},
        required=["name"],
        risk_level="medium",
    )
    async def open_app(name: str) -> str:
        denied = await _gate("open_app", RiskLevel.MEDIUM, f"Open app: {name}")
        if denied:
            return denied
        result = await desktop.open_app(name)
        return f"Opened {name}." if result.success else f"Couldn't open {name}: {result.error}"

    @executor.register(
        name="open_url",
        description="Open a website in the default browser.",
        parameters={"url": {"type": "string", "description": "URL or domain to open"}},
        required=["url"],
        risk_level="medium",
    )
    async def open_url(url: str) -> str:
        denied = await _gate("open_url", RiskLevel.MEDIUM, f"Open URL: {url}")
        if denied:
            return denied
        result = await desktop.open_url(url)
        return f"Opened {url}." if result.success else f"Couldn't open {url}: {result.error}"

    @executor.register(
        name="control_mac",
        description=(
            "Run an AppleScript to control or edit on-screen apps: open documents, "
            "type text, click buttons, change settings. Use for 'do X on my Mac' requests."
        ),
        parameters={"script": {"type": "string", "description": "AppleScript source"}},
        required=["script"],
        risk_level="high",
        requires_confirmation=True,
    )
    async def control_mac(script: str) -> str:
        denied = await _gate("control_mac", RiskLevel.HIGH, "Run AppleScript to control the Mac")
        if denied:
            return denied
        result = await desktop.run_applescript(script)
        return result.output if result.success else f"AppleScript failed: {result.error}"

    @executor.register(
        name="set_volume",
        description="Set the Mac's output volume to a level from 0 to 100.",
        parameters={"level": {"type": "string", "description": "Volume 0-100"}},
        required=["level"],
        risk_level="low",
    )
    async def set_volume(level: str) -> str:
        denied = await _gate("set_volume", RiskLevel.LOW, f"Set volume to {level}")
        if denied:
            return denied
        try:
            value = int(str(level).strip().rstrip("%"))
        except ValueError:
            return f"I didn't catch a volume level in '{level}'."
        result = await desktop.set_volume(value)
        clamped = max(0, min(100, value))
        if result.success:
            return f"Volume set to {clamped}%."
        return f"Couldn't set volume: {result.error}"

    @executor.register(
        name="type_text",
        description="Type text into whatever app is focused (dictation).",
        parameters={"text": {"type": "string", "description": "The text to type"}},
        required=["text"],
        risk_level="high",
    )
    async def type_text(text: str) -> str:
        denied = await _gate("type_text", RiskLevel.HIGH, f"Type text: {text}")
        if denied:
            return denied
        result = await desktop.type_text(text)
        return f'Typed: "{text}"' if result.success else f"Couldn't type: {result.error}"

    @executor.register(
        name="open_thing",
        description=(
            "Open something on the Mac by name — an app, a folder (Downloads, "
            "Documents…), a website, or a file path. Use for any 'open X' request."
        ),
        parameters={"target": {"type": "string", "description": "App, folder, site, or path"}},
        required=["target"],
        risk_level="medium",
    )
    async def open_thing(target: str) -> str:
        denied = await _gate("open_thing", RiskLevel.MEDIUM, f"Open: {target}")
        if denied:
            return denied
        result = await desktop.open_smart(target)
        return f"Opened {target}." if result.success else f"Couldn't open {target}: {result.error}"

    @executor.register(
        name="take_screenshot",
        description="Capture the screen to a PNG on the Desktop.",
        parameters={},
        risk_level="medium",
    )
    async def take_screenshot() -> str:
        denied = await _gate("take_screenshot", RiskLevel.MEDIUM, "Take a screenshot")
        if denied:
            return denied
        result = await desktop.take_screenshot()
        return result.output if result.success else f"Couldn't take screenshot: {result.error}"

    @executor.register(
        name="lock_screen",
        description="Lock the Mac by sleeping the display.",
        parameters={},
        risk_level="medium",
    )
    async def lock_screen() -> str:
        denied = await _gate("lock_screen", RiskLevel.MEDIUM, "Lock the screen")
        if denied:
            return denied
        result = await desktop.lock_screen()
        return "Screen locked." if result.success else f"Couldn't lock: {result.error}"

    @executor.register(
        name="media_control",
        description="Control music playback: play, pause, next, or previous.",
        parameters={"action": {"type": "string", "description": "play, pause, next, or previous"}},
        required=["action"],
        risk_level="low",
    )
    async def media_control(action: str) -> str:
        denied = await _gate("media_control", RiskLevel.LOW, f"Media: {action}")
        if denied:
            return denied
        result = await desktop.media_control(action)
        verb = {
            "play": "Playing",
            "pause": "Paused",
            "next": "Skipped to next",
            "previous": "Back to previous",
        }.get(action, "Toggled playback")
        return f"{verb}." if result.success else f"Couldn't control media: {result.error}"

    return executor
