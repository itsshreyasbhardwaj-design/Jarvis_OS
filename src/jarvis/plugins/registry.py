"""
Plugin Registry
===============
Manages plugin discovery, registration, and lifecycle.
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

from loguru import logger

from jarvis.plugins.base import JarvisPlugin, PluginContext, PluginMetadata


class PluginRegistry:
    """
    Central registry for all JARVIS plugins.

    Usage:
        registry = PluginRegistry(plugins_dir="plugins/")
        registry.register(CalendarPlugin())
        registry.register(EmailPlugin())

        await registry.start_all(context)
        await registry.stop_all()

        # Dynamic loading from directory
        await registry.load_from_directory("plugins/")
    """

    def __init__(self, plugins_dir: str | None = None) -> None:
        self._plugins: dict[str, JarvisPlugin] = {}
        self._started: list[str] = []
        self._plugins_dir = Path(plugins_dir) if plugins_dir else None

    def register(self, plugin: JarvisPlugin) -> None:
        """Register a plugin instance."""
        name = plugin.metadata.name
        if name in self._plugins:
            logger.warning(f"Plugin already registered: {name}. Replacing.")
        self._plugins[name] = plugin
        logger.info(
            f"Plugin registered: {name}@{plugin.metadata.version} "
            f"— {plugin.metadata.description}"
        )

    def unregister(self, name: str) -> bool:
        """Remove a plugin registration."""
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    async def start_all(self, context: PluginContext) -> None:
        """Start all registered plugins."""
        logger.info(f"Starting {len(self._plugins)} plugins...")
        for _name, plugin in self._plugins.items():
            await self._start_plugin(plugin, context)

    async def _start_plugin(
        self, plugin: JarvisPlugin, context: PluginContext
    ) -> bool:
        """Start a single plugin with error isolation."""
        try:
            await plugin.start(context)
            self._started.append(plugin.name)
            logger.success(f"  ✓ Plugin: {plugin.name}")
            return True
        except Exception as e:
            logger.error(f"  ✗ Plugin {plugin.name} failed to start: {e}")
            await plugin.on_error(e)
            return False

    async def stop_all(self) -> None:
        """Stop all started plugins in reverse order."""
        for name in reversed(self._started):
            plugin = self._plugins.get(name)
            if plugin:
                try:
                    await plugin.stop()
                    logger.debug(f"Plugin stopped: {name}")
                except Exception as e:
                    logger.warning(f"Plugin {name} stop error: {e}")

    async def load_from_directory(
        self, directory: str, context: PluginContext | None = None
    ) -> list[str]:
        """
        Dynamically load plugins from Python files in a directory.
        Each file should define a class named `Plugin` that extends JarvisPlugin.
        Returns list of successfully loaded plugin names.
        """
        plugin_dir = Path(directory)
        if not plugin_dir.is_dir():
            logger.warning(f"Plugin directory not found: {directory}")
            return []

        loaded = []
        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"jarvis_plugin_{py_file.stem}", py_file
                )
                if not spec or not spec.loader:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore

                plugin_cls = getattr(module, "Plugin", None)
                if plugin_cls and issubclass(plugin_cls, JarvisPlugin):
                    plugin = plugin_cls()
                    self.register(plugin)
                    if context:
                        await self._start_plugin(plugin, context)
                    loaded.append(plugin.name)
            except Exception as e:
                logger.error(f"Failed to load plugin from {py_file.name}: {e}")

        return loaded

    def get(self, name: str) -> JarvisPlugin | None:
        """Get a registered plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginMetadata]:
        """Return metadata for all registered plugins."""
        return [p.metadata for p in self._plugins.values()]

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)
