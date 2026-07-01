"""
User Preferences Store
======================
Persists user preferences learned from interactions or explicitly set.

Examples:
- "User prefers Chrome over Firefox"
- "User wants file operations confirmed"
- "User preferred response language: English"
- "User's work hours: 9am-6pm"
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from loguru import logger


class UserPreferences:
    """
    Key-value store for user preferences backed by JSON.

    Preferences are organized by namespace (e.g. "ui", "voice", "behavior").

    Usage:
        prefs = UserPreferences()
        prefs.set("ui.theme", "dark")
        prefs.set("behavior.confirm_file_ops", True)
        theme = prefs.get("ui.theme", default="dark")
    """

    def __init__(
        self, prefs_file: str = "data/memory/user_preferences.json"
    ) -> None:
        self._prefs_file = Path(prefs_file)
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load preferences from disk."""
        if self._prefs_file.exists():
            try:
                with open(self._prefs_file) as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load preferences: {e}")
                self._data = {}

    def _save(self) -> None:
        """Save preferences to disk."""
        self._prefs_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._prefs_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def set(self, key: str, value: Any) -> None:
        """Set a preference (supports dotted keys: "ui.theme")."""
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        d["_updated_at"] = time.time()
        self._save()
        logger.debug(f"Preference set: {key} = {value!r}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        keys = key.split(".")
        d = self._data
        for k in keys:
            if not isinstance(d, dict) or k not in d:
                return default
            d = d[k]
        return d

    def delete(self, key: str) -> None:
        """Delete a preference."""
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            if k not in d:
                return
            d = d[k]
        d.pop(keys[-1], None)
        self._save()

    def get_all(self, namespace: str | None = None) -> dict[str, Any]:
        """Return all preferences, optionally filtered by namespace."""
        if namespace:
            return dict(self._data.get(namespace, {}))
        return dict(self._data)

    def reset(self) -> None:
        """Reset all preferences to defaults."""
        self._data = {}
        self._save()
        logger.info("User preferences reset")
