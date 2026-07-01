"""
Google Gemini Provider
======================
Implements the AIProvider interface for Google Gemini models.
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
    ToolDefinition,
)


class GeminiProvider(AIProvider):
    """Google Gemini provider (gemini-1.5-pro, gemini-1.5-flash)."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro") -> None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._genai = genai
            self._model_name = model
            self._model = genai.GenerativeModel(model)
        except ImportError as e:
            raise ImportError(
                "google-generativeai required: pip install google-generativeai"
            ) from e
        logger.info(f"GeminiProvider initialized: {model}")

    @property
    def provider_name(self) -> str:
        return "Gemini (Google)"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def max_context_tokens(self) -> int:
        return 1_000_000  # Gemini 1.5 Pro context window

    async def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AIResponse:
        history = self._convert_messages(messages)
        last_user_msg = next(
            (m.content for m in reversed(messages) if m.role == Role.USER), ""
        )

        config = self._genai.GenerationConfig(
            max_output_tokens=max_tokens, temperature=temperature
        )

        with Timer() as timer:
            chat = self._model.start_chat(history=history[:-1])
            response = await chat.send_message_async(
                last_user_msg, generation_config=config
            )

        return AIResponse(
            content=response.text,
            model=self._model_name,
            provider="gemini",
            usage=TokenUsage(
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
            ),
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
        last_user_msg = next(
            (m.content for m in reversed(messages) if m.role == Role.USER), ""
        )
        config = self._genai.GenerationConfig(
            max_output_tokens=max_tokens, temperature=temperature
        )
        response = self._model.generate_content(
            last_user_msg, generation_config=config, stream=True
        )
        for chunk in response:
            if chunk.text:
                yield StreamChunk(content=chunk.text)
        yield StreamChunk(is_final=True, finish_reason="stop")

    async def count_tokens(self, messages: list[Message]) -> int:
        text = " ".join(m.content for m in messages)
        result = self._model.count_tokens(text)
        return result.total_tokens

    async def health_check(self) -> bool:
        try:
            response = self._model.generate_content("hi")
            return bool(response.text)
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue
            role = "user" if msg.role == Role.USER else "model"
            result.append({"role": role, "parts": [msg.content]})
        return result
