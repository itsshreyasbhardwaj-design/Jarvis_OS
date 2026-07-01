"""Desktop automation layer: files, keyboard, screen, apps."""

from jarvis.desktop.applications.launcher import ApplicationLauncher
from jarvis.desktop.automation.keyboard import KeyboardAutomation, MouseAutomation
from jarvis.desktop.file_system.navigator import FileInfo, FileNavigator
from jarvis.desktop.permissions import PermissionManager, PermissionRequest, RiskLevel
from jarvis.desktop.screen.capture import ScreenCapture, Screenshot

__all__ = [
    "ApplicationLauncher",
    "FileInfo",
    "FileNavigator",
    "KeyboardAutomation",
    "MouseAutomation",
    "PermissionManager",
    "PermissionRequest",
    "RiskLevel",
    "ScreenCapture",
    "Screenshot",
]
