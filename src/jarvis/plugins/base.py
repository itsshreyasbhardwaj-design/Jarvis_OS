"""
Plugin Base Class
=================
Every JARVIS plugin extends this base class.

A plugin is a self-contained capability module that:
- Declares its name, version, and description
- Registers tools with the ToolExecutor
- Subscribes to relevant events
- Has its own lifecycle (start/stop)
- Cannot modify core JARVIS functionality

Plugin contract:
- Plugins CANNOT access other plugins directly (only through events)
- Plugins CANNOT override core security or permission settings
- Plugins declare required permissions upfront (shown to user on install)
- Plugin failures are isolated — one broken plugin cannot crash JARVIS

Creating a plugin:
    from jarvis.plugins.base import JarvisPlugin, PluginMetadata, PluginTool
    from jarvis.ai.providers.base import ToolDefinition

    class MyPlugin(JarvisPlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="my_plugin",
                version="1.0.0",
                description="Does something awesome",
                author="Me",
                required_permissions=["low"],
            )

        async def start(self, context: PluginContext) -> None:
            context.tool_executor.register(
                "my_action",
                description="...",
                parameters={...},
                handler=self.my_action,
            )

        async def my_action(self, param: str) -> str:
            return f"Did: {param}"
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jarvis.ai.tool_executor import ToolExecutor
    from jarvis.core.event_bus import EventBus


@dataclass
class PluginMetadata:
    """Metadata about a plugin."""
    name: str
    version: str
    description: str
    author: str = ""
    homepage: str = ""
    required_permissions: list[str] = field(default_factory=list)
    # e.g. ["read_only", "low", "medium"]
    tags: list[str] = field(default_factory=list)
    min_jarvis_version: str = "0.1.0"


@dataclass
class PluginContext:
    """Context provided to each plugin at startup."""
    tool_executor: ToolExecutor
    event_bus: EventBus
    data_dir: str        # Plugin-specific data directory
    config: dict[str, Any] = field(default_factory=dict)


class JarvisPlugin(abc.ABC):
    """
    Abstract base class for all JARVIS plugins.

    Lifecycle:
    1. __init__()      — called at registration (no heavy work here)
    2. start(context)  — plugin initializes, registers tools/events
    3. stop()          — plugin cleans up resources
    """

    @property
    @abc.abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""

    @abc.abstractmethod
    async def start(self, context: PluginContext) -> None:
        """
        Initialize the plugin.
        Register tools, subscribe to events, connect to external services.
        """

    @abc.abstractmethod
    async def stop(self) -> None:
        """Clean up plugin resources."""

    async def on_error(self, error: Exception) -> None:  # noqa: B027
        """Called when the plugin encounters an unhandled error. Override to handle."""

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    def __repr__(self) -> str:
        return f"<Plugin:{self.metadata.name}@{self.metadata.version}>"
