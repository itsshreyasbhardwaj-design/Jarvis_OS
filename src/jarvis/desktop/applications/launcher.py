"""
Application Launcher
====================
Cross-platform application launching with permission checks.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from loguru import logger

from jarvis.desktop.permissions import PermissionManager, PermissionRequest, RiskLevel


class ApplicationLauncher:
    """
    Launch applications cross-platform.

    Usage:
        launcher = ApplicationLauncher(permissions=pm)
        await launcher.open_application("Chrome")
        await launcher.open_url("https://google.com")
        await launcher.open_file("~/Documents/report.pdf")
    """

    def __init__(self, permissions: PermissionManager) -> None:
        self._permissions = permissions

    async def open_application(self, app_name: str) -> None:
        """Launch an application by name."""
        result = await self._permissions.check(PermissionRequest(
            action_name="open_application",
            risk_level=RiskLevel.LOW,
            description=f"Open application: {app_name}",
            args={"app": app_name},
        ))
        if not result.granted:
            raise PermissionError(result.reason)

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._launch_app_sync(app_name)
        )
        logger.info(f"Launched: {app_name}")

    def _launch_app_sync(self, app_name: str) -> None:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-a", app_name])
        elif sys.platform == "win32":
            subprocess.Popen(["start", app_name], shell=True)
        else:
            subprocess.Popen([app_name.lower()])

    async def open_url(self, url: str) -> None:
        """Open a URL in the default browser."""
        import webbrowser
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: webbrowser.open(url)
        )
        logger.info(f"Opened URL: {url}")

    async def open_file(self, path: str) -> None:
        """Open a file with its default application."""
        abs_path = str(Path(path).expanduser().resolve())

        if not self._permissions.check_path(abs_path):
            raise PermissionError(f"Access denied: {abs_path}")

        result = await self._permissions.check(PermissionRequest(
            action_name="open_file",
            risk_level=RiskLevel.LOW,
            description=f"Open file: {abs_path}",
            args={"path": abs_path},
        ))
        if not result.granted:
            raise PermissionError(result.reason)

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._open_file_sync(abs_path)
        )

    def _open_file_sync(self, path: str) -> None:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform == "win32":
            subprocess.Popen(["start", path], shell=True)
        else:
            subprocess.Popen(["xdg-open", path])
