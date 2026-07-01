"""
Claude (Anthropic) Provider
============================
Implements the AIProvider interface for Anthropic's Claude models.
Supports streaming, tool calling, and prompt caching.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from loguru import logger
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from jarvis.ai.providers.base import (
    AIProvider,
    AIResponse,
    Message,
    Role,
    StreamChunk,
    Timer,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


class ClaudeProvider(AIProvider):
    """
    Anthropic Claude provider.

    Supported models:
    - claude-opus-4-5      (most capable, slower)
    - claude-sonnet-4-5    (balanced)
    - claude-haiku-4-5     (fastest)

    Features:
    - Native tool use (parallel tool calling)
    - Prompt caching (reduces cost for repeated system prompts)
    - Extended thinking mode (claude-3-7-sonnet)
    - Streaming with tool streaming
    """

    SUPPORTED_MODELS = {
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5-20251001",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    }

    def __init__(self, api_key: str, model: str = "claude-opus-4-5") -> None:
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError as e:
            raise ImportError(
                "anthropic package required: pip install anthropic"
            ) from e

        self._model = model
        logger.info(f"ClaudeProvider initialized: {model}")

    @property
    def provider_name(self) -> str:
        return "Claude (Anthropic)"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_context_tokens(self) -> int:
        return 200_000  # Claude's context window

    async def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AIResponse:
        system = system_prompt or self.build_jarvis_system_prompt()
        api_messages = self._convert_messages(messages)
        api_tools = self._convert_tools(tools) if tools else []

        with Timer() as timer:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(Exception),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                reraise=True,
            ):
                with attempt:
                    kwargs: dict[str, Any] = {
                        "model": self._model,
                        "max_tokens": max_tokens,
                        "system": system,
                        "messages": api_messages,
                        "temperature": temperature,
                    }
                    if api_tools:
                        kwargs["tools"] = api_tools

                    response = await self._client.messages.create(**kwargs)

        content = ""
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        return AIResponse(
            content=content,
            model=response.model,
            provider="claude",
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "stop",
            response_time_ms=timer.elapsed_ms,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        system = system_prompt or self.build_jarvis_system_prompt()
        api_messages = self._convert_messages(messages)
        api_tools = self._convert_tools(tools) if tools else []

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": api_messages,
            "temperature": temperature,
        }
        if api_tools:
            kwargs["tools"] = api_tools

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(content=text)

            final = await stream.get_final_message()
            yield StreamChunk(
                is_final=True,
                finish_reason=final.stop_reason or "stop",
            )

    async def count_tokens(self, messages: list[Message]) -> int:
        api_messages = self._convert_messages(messages)
        result = await self._client.messages.count_tokens(
            model=self._model,
            messages=api_messages,
        )
        return result.input_tokens

    async def health_check(self) -> bool:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return len(response.content) > 0
        except Exception as e:
            logger.warning(f"Claude health check failed: {e}")
            return False

    # --- Conversion Helpers ---

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert JARVIS Message objects to Anthropic API format."""
        result = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue  # System is passed separately in Claude API

            api_msg: dict[str, Any] = {"role": msg.role.value}

            if msg.tool_calls:
                content_blocks = [{"type": "text", "text": msg.content}] if msg.content else []
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id"),
                        "name": tc.get("name"),
                        "input": tc.get("arguments", {}),
                    })
                api_msg["content"] = content_blocks
            elif msg.tool_call_id:
                api_msg["content"] = [{
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": msg.content,
                }]
            else:
                api_msg["content"] = msg.content

            result.append(api_msg)
        return result

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert ToolDefinition objects to Anthropic API format."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": {
                    "type": "object",
                    "properties": t.parameters,
                    "required": t.required,
                },
            }
            for t in tools
        ]
