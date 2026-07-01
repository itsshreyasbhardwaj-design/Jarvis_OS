"""
Desktop Control (macOS)
=======================
Lets JARVIS act on the Mac: open applications, open URLs/files, and run
AppleScript to control or edit whatever is on screen. Uses the built-in
``open`` command and ``osascript`` — no extra native dependencies.

AppleScript that drives other apps' UIs (System Events keystrokes/clicks) needs
macOS **Automation/Accessibility** permission, granted once per app in
System Settings → Privacy & Security. Opening apps/URLs works without it.

Usage:
    ctrl = DesktopControl()
    await ctrl.open_app("Safari")
    await ctrl.open_url("apple.com")
    await ctrl.run_applescript('tell application "Notes" to activate')
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass

from loguru import logger

__all__ = ["ControlResult", "DesktopControl"]

# Spoken folder names → filesystem paths.
_FOLDERS = {
    "downloads": "~/Downloads",
    "documents": "~/Documents",
    "desktop": "~/Desktop",
    "home": "~",
    "applications": "/Applications",
    "apps": "/Applications",
    "pictures": "~/Pictures",
    "photos": "~/Pictures",
    "music": "~/Music",
    "movies": "~/Movies",
    "videos": "~/Movies",
    "trash": "~/.Trash",
}

# Spoken app names → real macOS application names.
_APP_ALIASES = {
    "email": "Mail", "mail": "Mail", "gmail": "Mail",
    "browser": "Safari", "the browser": "Safari", "web browser": "Safari",
    "settings": "System Settings", "system settings": "System Settings",
    "preferences": "System Settings", "system preferences": "System Settings",
    "calculator": "Calculator", "terminal": "Terminal", "calendar": "Calendar",
    "messages": "Messages", "texts": "Messages", "notes": "Notes",
    "music": "Music", "apple music": "Music", "itunes": "Music",
    "photos": "Photos", "maps": "Maps", "reminders": "Reminders",
    "finder": "Finder", "app store": "App Store",
}
_WEB_TLDS = {
    "com", "org", "net", "io", "dev", "ai", "co", "edu", "gov",
    "app", "xyz", "me", "tv", "us", "uk", "in",
}


def _folder_path(name: str) -> str:
    """Resolve a spoken folder name (or raw path) to an absolute path (pure)."""
    key = name.strip().lower().removeprefix("my ").removesuffix(" folder").strip()
    return os.path.expanduser(_FOLDERS.get(key, name))


def _screenshot_path() -> tuple[str, str]:
    """Return (dest_path, filename) for a new Desktop screenshot (pure)."""
    filename = f"JARVIS-screenshot-{int(time.time())}.png"
    return os.path.join(os.path.expanduser("~"), "Desktop", filename), filename


@dataclass
class ControlResult:
    """Outcome of a desktop-control action."""

    success: bool
    output: str = ""
    error: str = ""


class DesktopControl:
    """Open and control macOS apps via ``open`` and AppleScript."""

    def __init__(self, *, timeout: float = 20.0) -> None:
        self._timeout = timeout

    async def open_app(self, name: str) -> ControlResult:
        """Launch (or focus) an application by name."""
        return await self._run(["open", "-a", name], f"opened {name}")

    async def open_url(self, url: str) -> ControlResult:
        """Open a URL in the default browser."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return await self._run(["open", url], f"opened {url}")

    async def open_path(self, path: str) -> ControlResult:
        """Open a file or folder with its default app / Finder."""
        return await self._run(["open", path], f"opened {path}")

    async def run_applescript(self, script: str) -> ControlResult:
        """Run an AppleScript snippet (can control/edit on-screen apps)."""
        return await self._run(["osascript", "-e", script], "ran AppleScript")

    async def set_volume(self, level: int) -> ControlResult:
        """Set system output volume (0-100). Needs no special permission."""
        level = max(0, min(100, int(level)))
        return await self.run_applescript(f"set volume output volume {level}")

    async def type_text(self, text: str) -> ControlResult:
        """Type text into the frontmost app (needs Accessibility permission)."""
        safe = text.replace("\\", "\\\\").replace('"', '\\"')
        return await self.run_applescript(
            f'tell application "System Events" to keystroke "{safe}"'
        )

    async def open_folder(self, name: str) -> ControlResult:
        """Open a folder in Finder by common name (Downloads, Documents…) or path."""
        return await self._run(["open", _folder_path(name)], f"opened {name}")

    async def open_smart(self, target: str) -> ControlResult:
        """Open the right thing for a spoken target: folder, app, website, or path."""
        text = target.strip()
        is_my = text.lower().startswith("my ")
        key = text.lower().removeprefix("my ").removesuffix(" folder").strip()
        if is_my and key in _FOLDERS:  # "my downloads" → the folder
            return await self.open_folder(key)
        if key in _APP_ALIASES:  # "email", "music", "settings" → the app
            return await self.open_app(_APP_ALIASES[key])
        if key in _FOLDERS:  # "downloads", "documents" → the folder
            return await self.open_folder(key)
        if text.startswith(("/", "~")):
            return await self.open_path(text)
        if " " not in text and "." in text and not text.startswith("."):
            tld = text.rsplit(".", 1)[-1].lower()
            if tld in _WEB_TLDS:  # "apple.com" → website
                return await self.open_url(text)
            return await self.open_path(text)  # "notes.txt" → file
        return await self.open_app(text)  # anything else → an app

    async def take_screenshot(self) -> ControlResult:
        """Capture the screen to a PNG on the Desktop (needs Screen Recording perm)."""
        dest, filename = _screenshot_path()
        return await self._run(
            ["screencapture", "-x", dest], f"screenshot saved to Desktop: {filename}"
        )

    async def lock_screen(self) -> ControlResult:
        """Sleep the display (locks the Mac if a password is required on wake)."""
        return await self._run(["pmset", "displaysleepnow"], "screen locked")

    async def media_control(self, action: str) -> ControlResult:
        """Control the active music player (Spotify or Apple Music)."""
        verb = {
            "play": "play",
            "pause": "pause",
            "playpause": "playpause",
            "next": "next track",
            "previous": "previous track",
        }.get(action, "playpause")
        script = (
            'tell application "System Events"\n'
            '  if (name of processes) contains "Spotify" then\n'
            f'    tell application "Spotify" to {verb}\n'
            '  else if (name of processes) contains "Music" then\n'
            f'    tell application "Music" to {verb}\n'
            "  end if\n"
            "end tell"
        )
        return await self.run_applescript(script)

    async def get_frontmost_app(self) -> str:
        """Name of the app currently in the foreground."""
        result = await self.run_applescript(
            'tell application "System Events" to return name of '
            "first application process whose frontmost is true"
        )
        return result.output if result.success else "unknown"

    async def _run(self, cmd: list[str], success_msg: str) -> ControlResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except (TimeoutError, OSError) as exc:
            logger.warning("Desktop command {} failed: {}", cmd[:2], exc)
            return ControlResult(success=False, error=str(exc))

        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        if proc.returncode == 0:
            return ControlResult(success=True, output=out or success_msg)
        logger.warning("Desktop command {} exit {}: {}", cmd[:2], proc.returncode, err)
        return ControlResult(success=False, output=out, error=err or "command failed")
