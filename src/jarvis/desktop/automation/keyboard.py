"""
Keyboard & Mouse Automation
============================
Safe keyboard and mouse input synthesis using pynput (CGEvent-based).

Stack (v2 — June 2026):
- pynput: CGEvent-based keyboard/mouse synthesis on macOS
  Replaces pyautogui (unreliable on macOS Retina/multi-monitor)
- atomacos: Accessibility API for clicking by label/role (companion to pynput)

Design:
- All actions gated behind PermissionManager (RiskLevel.LOW)
- No global key capture without explicit grant
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from jarvis.desktop.permissions import PermissionManager, PermissionRequest, RiskLevel


class KeyboardAutomation:
    """
    Safe keyboard automation using pynput CGEvent.

    Usage:
        kb = KeyboardAutomation(permission_manager)
        await kb.type_text("Hello, JARVIS!")
        await kb.press_hotkey("cmd", "c")
        await kb.press_key("return")
    """

    def __init__(self, permission_manager: PermissionManager) -> None:
        self._permissions = permission_manager
        self._controller: Any = None

    async def type_text(self, text: str, interval: float = 0.0) -> None:
        """Type a string of text character by character."""
        result = await self._permissions.check(PermissionRequest(
            action_name="type_text",
            risk_level=RiskLevel.LOW,
            description=f"Type text: '{text[:30]}{'...' if len(text) > 30 else ''}'",
        ))
        if not result.granted:
            logger.warning("type_text blocked: {}", result.reason)
            return

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._type_sync(text, interval)
        )

    def _type_sync(self, text: str, interval: float) -> None:
        """Blocking keyboard type using pynput."""
        try:
            from pynput.keyboard import Controller  # type: ignore[import-untyped]
            controller = Controller()
            if interval > 0:
                import time
                for char in text:
                    controller.type(char)
                    time.sleep(interval)
            else:
                controller.type(text)
        except ImportError as exc:
            raise ImportError(
                "pynput required: pip install pynput>=1.7.6"
            ) from exc

    async def press_hotkey(self, *keys: str) -> None:
        """Press a key combination (e.g., 'cmd', 'c' for Copy)."""
        result = await self._permissions.check(PermissionRequest(
            action_name="press_hotkey",
            risk_level=RiskLevel.LOW,
            description=f"Hotkey: {'+'.join(keys)}",
        ))
        if not result.granted:
            logger.warning("press_hotkey blocked: {}", result.reason)
            return

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._hotkey_sync(keys)
        )

    def _hotkey_sync(self, keys: tuple[str, ...]) -> None:
        """Blocking hotkey press using pynput."""
        try:
            from pynput.keyboard import Controller, Key  # type: ignore[import-untyped]
            controller = Controller()
            # Map string names to pynput Key objects
            key_map = {
                "cmd": Key.cmd, "ctrl": Key.ctrl, "alt": Key.alt,
                "shift": Key.shift, "return": Key.enter, "enter": Key.enter,
                "tab": Key.tab, "esc": Key.esc, "space": Key.space,
                "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
                "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
                "backspace": Key.backspace, "delete": Key.delete,
            }
            resolved = [key_map.get(k, k) for k in keys]
            # Press all modifier keys, then action key, then release
            for key in resolved[:-1]:
                controller.press(key)
            controller.press(resolved[-1])
            controller.release(resolved[-1])
            for key in reversed(resolved[:-1]):
                controller.release(key)
        except ImportError as exc:
            raise ImportError(
                "pynput required: pip install pynput>=1.7.6"
            ) from exc

    async def press_key(self, key: str) -> None:
        """Press and release a single key."""
        result = await self._permissions.check(PermissionRequest(
            action_name="press_key",
            risk_level=RiskLevel.LOW,
            description=f"Press key: {key}",
        ))
        if not result.granted:
            logger.warning("press_key blocked: {}", result.reason)
            return

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._press_sync(key)
        )

    def _press_sync(self, key: str) -> None:
        """Blocking single key press using pynput."""
        try:
            from pynput.keyboard import Controller, Key  # type: ignore[import-untyped]
            controller = Controller()
            key_map = {
                "return": Key.enter, "enter": Key.enter, "tab": Key.tab,
                "esc": Key.esc, "space": Key.space, "backspace": Key.backspace,
                "delete": Key.delete, "up": Key.up, "down": Key.down,
                "left": Key.left, "right": Key.right,
            }
            k = key_map.get(key, key)
            controller.press(k)
            controller.release(k)
        except ImportError as exc:
            raise ImportError(
                "pynput required: pip install pynput>=1.7.6"
            ) from exc


class MouseAutomation:
    """
    Safe mouse control using pynput.

    Usage:
        mouse = MouseAutomation(permission_manager)
        await mouse.click(x=100, y=200)
        await mouse.scroll(dx=0, dy=-3)
    """

    def __init__(self, permission_manager: PermissionManager) -> None:
        self._permissions = permission_manager

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Click at screen coordinates."""
        result = await self._permissions.check(PermissionRequest(
            action_name="mouse_click",
            risk_level=RiskLevel.LOW,
            description=f"Click at ({x}, {y})",
        ))
        if not result.granted:
            logger.warning("mouse_click blocked: {}", result.reason)
            return

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._click_sync(x, y, button)
        )

    def _click_sync(self, x: int, y: int, button: str) -> None:
        try:
            from pynput.mouse import Button, Controller  # type: ignore[import-untyped]
            btn_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
            controller = Controller()
            controller.position = (x, y)
            controller.click(btn_map.get(button, Button.left))
        except ImportError as exc:
            raise ImportError("pynput required: pip install pynput>=1.7.6") from exc

    async def scroll(self, dx: int = 0, dy: int = -3) -> None:
        """Scroll the mouse wheel."""
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._scroll_sync(dx, dy)
        )

    def _scroll_sync(self, dx: int, dy: int) -> None:
        try:
            from pynput.mouse import Controller  # type: ignore[import-untyped]
            controller = Controller()
            controller.scroll(dx, dy)
        except ImportError as exc:
            raise ImportError("pynput required: pip install pynput>=1.7.6") from exc
