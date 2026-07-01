# Create a New JARVIS Plugin

Scaffold a new plugin for JARVIS OS. Plugins extend JARVIS with new capabilities
without modifying core code.

## Plugin being created: $ARGUMENTS

## Steps

### 1. Create the directory structure
```
src/jarvis/plugins/$ARGUMENTS/
├── __init__.py
├── plugin.py      ← Main plugin class (MUST be named Plugin)
├── plugin.json    ← Metadata
└── README.md      ← Usage docs
```

### 2. plugin.json
```json
{
  "name": "$ARGUMENTS",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": "Shrey",
  "min_jarvis_version": "0.1.0",
  "permissions": ["voice", "memory"]
}
```

### 3. plugin.py template
```python
"""$ARGUMENTS plugin for JARVIS OS."""
from __future__ import annotations

from loguru import logger

from jarvis.plugins.base import JarvisPlugin, PluginContext, PluginMetadata
from jarvis.security.permissions import RiskLevel
from jarvis.ai.tool_executor import ToolResult


class Plugin(JarvisPlugin):
    """$ARGUMENTS — one sentence description."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="$ARGUMENTS",
            version="1.0.0",
            description="What this plugin does",
            author="Shrey",
        )

    async def start(self, context: PluginContext) -> None:
        """Initialize plugin — register tools and subscribe to events."""
        self._context = context

        # Register tool(s) this plugin provides
        @context.tool_executor.register(
            name="${ARGUMENTS}_main_action",
            description="What this action does",
            risk_level=RiskLevel.LOW,
            timeout=15.0,
        )
        async def main_action(query: str) -> ToolResult:
            logger.info("[{}] Handling: {}", self.metadata.name, query)
            try:
                result = await self._do_work(query)
                return ToolResult(success=True, data={"result": result})
            except Exception as e:
                return ToolResult(success=False, error=str(e))

        # Subscribe to relevant events (optional)
        await context.event_bus.subscribe(
            "jarvis.voice.transcription_complete",
            self._on_voice_input,
        )
        logger.success("[{}] Plugin started", self.metadata.name)

    async def stop(self) -> None:
        """Cleanup resources."""
        logger.info("[{}] Plugin stopped", self.metadata.name)

    async def on_error(self, error: Exception) -> None:
        logger.error("[{}] Error: {}", self.metadata.name, error)

    async def _on_voice_input(self, event: Any) -> None:
        text = event.data.get("text", "").lower()
        if "$ARGUMENTS" in text:
            # Handle the voice command
            pass

    async def _do_work(self, query: str) -> str:
        # Plugin logic here
        return f"Result for: {query}"
```

### 4. Install the plugin
```bash
jarvis plugin install src/jarvis/plugins/$ARGUMENTS/
```

### 5. Rules
- Plugin class MUST be named exactly `Plugin`
- Never import from other plugins
- Store state in `context.data_dir` (persistent across restarts)
- All plugin methods must be async
- Always handle exceptions in tool functions — never let them propagate
