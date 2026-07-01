"""
OpenAI Provider
===============
Implements the AIProvider interface for OpenAI's GPT models.
Supports streaming, parallel tool calling, and vision.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

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


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider (GPT-4o, GPT-4-turbo, etc.)."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
        except ImportError as e:
            raise ImportError("openai package required: pip install openai") from e
        self._model = model
        logger.info(f"OpenAIProvider initialized: {model}")

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_context_tokens(self) -> int:
        return 128_000

    async def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AIResponse:
        api_messages = self._convert_messages(messages, system_prompt)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t.to_dict()} for t in tools]
            kwargs["tool_choice"] = "auto"

        with Timer() as timer:
            response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            import json
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                ))

        return AIResponse(
            content=msg.content or "",
            model=response.model,
            provider="openai",
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            ),
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
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
        api_messages = self._convert_messages(messages, system_prompt)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield StreamChunk(content=delta.content)
            if chunk.choices and chunk.choices[0].finish_reason:
                yield StreamChunk(
                    is_final=True,
                    finish_reason=chunk.choices[0].finish_reason,
                )

    async def count_tokens(self, messages: list[Message]) -> int:
        # Approximation: 4 chars per token
        total_chars = sum(len(m.content) for m in messages)
        return total_chars // 4

    async def health_check(self) -> bool:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return bool(resp.choices)
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False

    def _convert_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        sys_prompt = system_prompt or self.build_jarvis_system_prompt()
        result.append({"role": "system", "content": sys_prompt})

        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue
            result.append({"role": msg.role.value, "content": msg.content})

        return result
