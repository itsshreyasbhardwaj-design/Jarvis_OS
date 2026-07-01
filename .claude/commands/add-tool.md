# Add a New JARVIS Tool

Add a new tool to the JARVIS tool executor. A tool is a function JARVIS can call
when responding to voice/text commands.

## Steps

1. **Identify the right module** for this tool:
   - Desktop actions (click, type, screenshot) → `src/jarvis/desktop/controller.py`
   - Browser actions (navigate, extract) → `src/jarvis/browser/controller.py`
   - Memory operations → `src/jarvis/memory/`
   - System info (CPU, disk, apps) → `src/jarvis/desktop/controller.py`
   - New domain → create `src/jarvis/{domain}/tools.py`

2. **Implement the tool function**:
```python
from jarvis.ai.tool_executor import tool_executor, ToolResult
from jarvis.security.permissions import RiskLevel

@tool_executor.register(
    name="$ARGUMENTS",          # snake_case verb_noun
    description="One clear sentence: what this does",
    risk_level=RiskLevel.LOW,   # READ_ONLY | LOW | MEDIUM | HIGH | CRITICAL
    timeout=10.0,               # seconds before auto-cancel
    requires_confirmation=False, # True for destructive/irreversible actions
    parameters={
        "param_name": {
            "type": "string",
            "description": "What this param controls",
            "required": True,
        }
    },
)
async def $ARGUMENTS(param_name: str) -> ToolResult:
    """One-line docstring matching description above."""
    try:
        # Always check permission for anything above READ_ONLY
        result = await do_the_thing(param_name)
        return ToolResult(success=True, data={"result": result})
    except Exception as e:
        logger.error("Tool {} failed: {}", "$ARGUMENTS", e)
        return ToolResult(success=False, error=str(e))
```

3. **Write the test** in `tests/unit/test_ai/test_tools.py`:
```python
@pytest.mark.asyncio
async def test_$ARGUMENTS(permissive_permissions):
    result = await $ARGUMENTS(param_name="test_value")
    assert result.success
    assert "result" in result.data
```

4. **Risk level guide**:
   - `READ_ONLY` — reading files, getting info, no side effects
   - `LOW` — opening apps, non-destructive UI clicks
   - `MEDIUM` — writing files, sending messages, creating items
   - `HIGH` — deleting files, system changes, purchases
   - `CRITICAL` — system settings, privileged operations
