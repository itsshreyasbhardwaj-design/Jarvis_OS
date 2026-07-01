"""
Tool Execution Engine
=====================
Executes AI-requested tool calls safely with permission checks,
timeout enforcement, and result formatting.

Flow:
  AI Response → ToolCall → Permission Check → Sandbox → Execute → Result
                                    ↓
                          Confirmation Dialog (for sensitive tools)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from loguru import logger

from jarvis.ai.providers.base import Message, Role, ToolCall, ToolDefinition

# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------


@dataclass
class RegisteredTool:
    """A tool registered with the executor."""
    definition: ToolDefinition
    handler: Callable[..., Coroutine[Any, Any, Any]]
    requires_confirmation: bool = False    # Show dialog before executing
    timeout_seconds: float = 30.0
    risk_level: str = "low"               # low | medium | high | critical


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0

    def to_message(self) -> Message:
        """Convert tool result to a Message for the next AI turn."""
        content = str(self.output) if self.success else f"Error: {self.error}"
        return Message(
            role=Role.TOOL,
            content=content,
            tool_call_id=self.tool_call_id,
            name=self.tool_name,
        )


# ---------------------------------------------------------------------------
# Tool Executor
# ---------------------------------------------------------------------------


class ToolExecutor:
    """
    Executes tool calls requested by the AI with safety guardrails.

    Usage:
        executor = ToolExecutor()

        @executor.register("open_application", risk_level="low")
        async def open_app(name: str) -> str:
            # ... implementation
            return f"Opened {name}"

        results = await executor.execute_all(ai_response.tool_calls)
    """

    def __init__(
        self,
        confirmation_callback: Callable[  # noqa: E501
            [str, dict[str, Any]], Coroutine[Any, Any, bool]
        ] | None = None,
    ) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._confirmation_callback = confirmation_callback or self._default_confirm
        self._execution_count = 0
        self._error_count = 0

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        required: list[str] | None = None,
        requires_confirmation: bool = False,
        risk_level: str = "low",
        timeout_seconds: float = 30.0,
    ) -> Callable:
        """Decorator for registering a tool handler."""
        def decorator(func: Callable) -> Callable:
            definition = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                required=required or [],
            )
            self._tools[name] = RegisteredTool(
                definition=definition,
                handler=func,
                requires_confirmation=requires_confirmation,
                timeout_seconds=timeout_seconds,
                risk_level=risk_level,
            )
            logger.debug(f"Tool registered: {name} (risk={risk_level})")
            return func
        return decorator

    @property
    def tool_definitions(self) -> list[ToolDefinition]:
        """Return definitions for all registered tools (passed to AI)."""
        return [t.definition for t in self._tools.values()]

    async def execute_all(
        self, tool_calls: list[ToolCall]
    ) -> list[ToolResult]:
        """Execute all requested tool calls, with parallelism for independent tools."""
        tasks = [self._execute_one(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)

    async def _execute_one(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool = self._tools.get(tool_call.name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Unknown tool: {tool_call.name}",
            )

        # Confirmation check for sensitive operations
        if tool.requires_confirmation:
            approved = await self._confirmation_callback(
                tool_call.name, tool_call.arguments
            )
            if not approved:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    success=False,
                    error="User denied tool execution",
                )

        # Execute with timeout
        import time
        start = time.perf_counter()
        try:
            output = await asyncio.wait_for(
                tool.handler(**tool_call.arguments),
                timeout=tool.timeout_seconds,
            )
            elapsed = (time.perf_counter() - start) * 1000
            self._execution_count += 1
            logger.debug(
                f"Tool executed: {tool_call.name} "
                f"({elapsed:.1f}ms)"
            )
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=True,
                output=output,
                execution_time_ms=elapsed,
            )
        except TimeoutError:
            self._error_count += 1
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Tool timed out after {tool.timeout_seconds}s",
            )
        except Exception as e:
            self._error_count += 1
            logger.error(f"Tool error ({tool_call.name}): {e}")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=str(e),
            )

    @staticmethod
    async def _default_confirm(name: str, args: dict[str, Any]) -> bool:
        """Default confirmation: log and auto-approve (replace with UI dialog)."""
        logger.warning(
            f"Auto-confirming tool call: {name}({args}) "
            "(connect UI confirmation dialog in production)"
        )
        return True
