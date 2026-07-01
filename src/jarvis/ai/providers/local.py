"""
Local Model Provider
====================
Runs local LLMs via llama.cpp (GGUF format).
Suitable for offline use, sensitive data, or cost-free inference.

Supported models: LLaMA 3, Mistral, Phi-3, Qwen, etc.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
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


class LocalProvider(AIProvider):
    """
    Local LLM provider using llama-cpp-python.

    Requirements:
        pip install llama-cpp-python
        Download a GGUF model file and set JARVIS_LOCAL_MODEL_PATH
    """

    def __init__(self, model_path: str, context_size: int = 8192) -> None:
        self._model_path = Path(model_path)
        self._context_size = context_size
        self._llm: Any = None

        if not self._model_path.exists():
            logger.warning(
                f"Local model not found: {model_path}. "
                "Provider will fail on first use."
            )

    def _ensure_loaded(self) -> None:
        """Lazy-load the model on first use."""
        if self._llm is not None:
            return
        try:
            from llama_cpp import Llama
            logger.info(f"Loading local model: {self._model_path}")
            self._llm = Llama(
                model_path=str(self._model_path),
                n_ctx=self._context_size,
                n_threads=4,
                verbose=False,
            )
            logger.success(f"Local model loaded: {self._model_path.name}")
        except ImportError as e:
            raise ImportError(
                "llama-cpp-python required for local models: "
                "pip install llama-cpp-python"
            ) from e

    @property
    def provider_name(self) -> str:
        return f"Local ({self._model_path.stem})"

    @property
    def model_name(self) -> str:
        return self._model_path.stem

    @property
    def max_context_tokens(self) -> int:
        return self._context_size

    async def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AIResponse:
        self._ensure_loaded()
        prompt = self._build_prompt(messages, system_prompt)

        with Timer() as timer:
            output = self._llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                echo=False,
            )

        content = output["choices"][0]["text"].strip()
        usage = output.get("usage", {})

        return AIResponse(
            content=content,
            model=self.model_name,
            provider="local",
            usage=TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            ),
            finish_reason=output["choices"][0].get("finish_reason", "stop"),
            response_time_ms=timer.elapsed_ms,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        self._ensure_loaded()
        prompt = self._build_prompt(messages, system_prompt)

        for chunk in self._llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        ):
            text = chunk["choices"][0]["text"]
            finish = chunk["choices"][0].get("finish_reason")
            if text:
                yield StreamChunk(content=text)
            if finish:
                yield StreamChunk(is_final=True, finish_reason=finish)

    async def count_tokens(self, messages: list[Message]) -> int:
        self._ensure_loaded()
        text = " ".join(m.content for m in messages)
        tokens = self._llm.tokenize(text.encode())
        return len(tokens)

    async def health_check(self) -> bool:
        return self._model_path.exists()

    def _build_prompt(
        self, messages: list[Message], system_prompt: str | None
    ) -> str:
        """Build a chat ML formatted prompt."""
        system = system_prompt or self.build_jarvis_system_prompt()
        parts = [f"<|system|>\n{system}<|end|>"]
        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue
            tag = "user" if msg.role == Role.USER else "assistant"
            parts.append(f"<|{tag}|>\n{msg.content}<|end|>")
        parts.append("<|assistant|>")
        return "\n".join(parts)
