"""
AI Provider Abstract Base
=========================
Defines the contract all AI providers must implement.
Switching between Claude, OpenAI, Gemini, or local models
requires only a config change — no code changes.

Design principles:
- Stream-first: All providers support async streaming
- Tool-calling: Standard interface for function/tool calls
- Cost tracking: Token usage is always reported
- Retry/backoff: Handled at the base level via tenacity
- Timeout enforcement: No runaway API calls
"""

from __future__ import annotations

import abc
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Message Types
# ---------------------------------------------------------------------------


class Role(StrEnum):
    """Message role in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A single message in a conversation."""
    role: Role
    content: str
    name: str | None = None           # For tool/function calls
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None   # For tool results


@dataclass
class ToolDefinition:
    """
    Defines a tool/function that the AI can call.
    Maps to OpenAI function calling, Claude tool use, Gemini function calling.
    """
    name: str
    description: str
    parameters: dict[str, Any]        # JSON Schema
    required: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }


@dataclass
class ToolCall:
    """A tool/function invocation requested by the AI."""
    id: str
    name: str
    arguments: dict[str, Any]


# ---------------------------------------------------------------------------
# Response Types
# ---------------------------------------------------------------------------


@dataclass
class TokenUsage:
    """Token consumption for cost tracking."""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class AIResponse:
    """Complete response from an AI provider."""
    content: str
    model: str
    provider: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"       # stop | length | tool_calls | error
    response_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """A single chunk from a streaming response."""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    is_final: bool = False
    finish_reason: str | None = None


# ---------------------------------------------------------------------------
# AI Provider Base Class
# ---------------------------------------------------------------------------


class AIProvider(abc.ABC):
    """
    Abstract base class for all AI providers.

    Concrete implementations: ClaudeProvider, OpenAIProvider,
    GeminiProvider, LocalProvider.

    All methods are async and support cancellation.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'Claude (Anthropic)'."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Active model identifier."""

    @property
    @abc.abstractmethod
    def max_context_tokens(self) -> int:
        """Maximum context window size in tokens."""

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AIResponse:
        """
        Send a conversation and get a complete response.

        Args:
            messages:      Conversation history
            tools:         Available tools for function calling
            max_tokens:    Maximum response length
            temperature:   Creativity (0.0 = deterministic, 1.0 = creative)
            system_prompt: Override the default system prompt

        Returns:
            Complete AIResponse with content, usage, and optional tool calls
        """

    @abc.abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Send a conversation and stream the response chunk by chunk.
        Yields StreamChunk objects until is_final=True.
        """

    @abc.abstractmethod
    async def count_tokens(self, messages: list[Message]) -> int:
        """Estimate token count for a set of messages."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Verify the provider is reachable and API keys are valid."""

    # --- Template Methods (shared across providers) ---

    def _measure_time(self) -> Timer:
        """Context manager for measuring response time."""
        return Timer()

    def build_jarvis_system_prompt(self) -> str:
        """
        Default JARVIS system prompt. Providers can override.
        """
        return """You are JARVIS, a world-class AI personal desktop assistant.
You are precise, efficient, and always act in the user's best interests.

Core principles:
1. ALWAYS ask for confirmation before taking destructive or irreversible actions
   (deleting files, sending messages, modifying system settings)
2. Be concise but thorough — respect the user's time
3. When uncertain, state your uncertainty clearly
4. Report what you are doing before you do it
5. Never hallucinate file paths, system states, or capabilities

You have access to the user's desktop, files, browser, and applications.
Use these capabilities carefully and transparently."""


class Timer:
    """Context manager for measuring elapsed time in milliseconds."""

    def __init__(self) -> None:
        self._start = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
