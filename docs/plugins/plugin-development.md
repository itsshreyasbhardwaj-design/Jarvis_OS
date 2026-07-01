# Plugin Development Guide

JARVIS plugins are Python classes that register tools, subscribe to events, and clean up on shutdown. They are dynamically loaded from `~/.jarvis/plugins/` or configured plugin directories.

---

## Minimal Plugin

```python
# my_plugin/plugin.py
from jarvis.plugins.base import JarvisPlugin, PluginMetadata, PluginContext
from jarvis.desktop.permissions import RiskLevel

class Plugin(JarvisPlugin):
    """
    The class must be named exactly `Plugin`.
    JARVIS discovers it by this name in the module.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="A minimal example plugin",
            author="Your Name",
        )

    async def start(self, context: PluginContext) -> None:
        """Register tools and subscribe to events here."""
        context.tool_executor.register(
            name="greet",
            description="Greet someone by name",
            parameters={
                "name": {
                    "type": "string",
                    "description": "Name to greet",
                }
            },
            required=["name"],
            risk_level=RiskLevel.READ_ONLY,
        )(self._greet)

    async def _greet(self, name: str) -> str:
        return f"Hello, {name}! JARVIS at your service."

    async def stop(self) -> None:
        """Clean up resources here."""
        pass
```

---

## PluginContext API

```python
class PluginContext:
    tool_executor: ToolExecutor    # Register tools
    event_bus: EventBus            # Subscribe/publish events
    data_dir: Path                 # Plugin-specific data directory
    config: dict[str, Any]        # Plugin configuration from settings
```

---

## Tool Registration

```python
context.tool_executor.register(
    name="my_tool",                    # Snake_case, unique across all plugins
    description="What this tool does", # Shown to AI — be descriptive
    parameters={                        # JSON Schema for arguments
        "file_path": {
            "type": "string",
            "description": "Absolute path to the file",
        },
        "encoding": {
            "type": "string",
            "enum": ["utf-8", "latin-1"],
            "description": "File encoding",
        }
    },
    required=["file_path"],            # Required parameters
    risk_level=RiskLevel.MEDIUM,       # Permission required
    requires_confirmation=True,         # Ask user before running
    timeout_seconds=30.0,              # Max execution time
)(my_async_function)
```

---

## Event Subscription

```python
async def start(self, context: PluginContext) -> None:
    # Subscribe to events
    context.event_bus.subscribe(
        "VoiceCommand*",
        self._on_voice,
        owner=self.name,
    )

async def _on_voice(self, event) -> None:
    if "weather" in event.text.lower():
        await self._get_weather()
```

---

## Plugin Directory Structure

```
~/.jarvis/plugins/
└── my-plugin/
    ├── plugin.py          # Required: contains class Plugin(JarvisPlugin)
    ├── requirements.txt   # Optional: extra dependencies
    └── README.md          # Optional: documentation
```

---

## Installing a Plugin

```bash
# Copy to plugins directory
cp -r my-plugin/ ~/.jarvis/plugins/

# Or via CLI
jarvis install-plugin ./path/to/my-plugin/

# Install dependencies
pip install -r ~/.jarvis/plugins/my-plugin/requirements.txt
```

---

## Best Practices

**DO:**
- Assign the correct `RiskLevel` — err toward higher when unsure
- Set `requires_confirmation=True` for any action that modifies state
- Handle errors inside your tool functions and return descriptive messages
- Clean up all resources (connections, file handles) in `stop()`
- Use `context.data_dir` for persistent data storage
- Log with `from loguru import logger`

**DON'T:**
- Import from `jarvis.core` directly — use `context`
- Block the event loop — use `asyncio.to_thread()` for CPU/I/O work
- Store secrets in plain text — use `context.credential_store`
- Assume your plugin loads before others — plugins load in alphabetical order
