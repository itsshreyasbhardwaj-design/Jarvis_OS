"""
AI Context Manager
==================
Manages the conversation context window, ensuring messages fit within
token limits while preserving important context (system prompt,
recent turns, pinned messages).

Strategy:
1. Always keep the system prompt
2. Always keep the N most recent messages
3. Fill remaining space with older messages (newest first)
4. Summarize very old context rather than dropping it entirely
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from jarvis.ai.providers.base import AIProvider, Message


@dataclass
class ContextConfig:
    """Configuration for context management."""
    max_tokens: int = 100_000        # Hard limit from provider
    target_tokens: int = 80_000     # Target (leave headroom)
    min_recent_messages: int = 10   # Always keep last N messages
    system_prompt_reserve: int = 2000  # Tokens reserved for system prompt


class ContextManager:
    """
    Manages AI conversation context to stay within token limits.

    Usage:
        ctx = ContextManager(provider, config)
        ctx.add_message(Message(role=Role.USER, content="Hello"))
        messages = await ctx.get_context()  # Trimmed to fit token budget
    """

    def __init__(
        self,
        provider: AIProvider,
        config: ContextConfig | None = None,
    ) -> None:
        self._provider = provider
        self._config = config or ContextConfig()
        self._messages: list[Message] = []
        self._pinned: list[Message] = []  # Never trimmed
        self._total_tokens = 0

    def add_message(self, message: Message) -> None:
        """Add a message to the context."""
        self._messages.append(message)

    def pin_message(self, message: Message) -> None:
        """Pin a message so it's never trimmed (e.g., important instructions)."""
        self._pinned.append(message)

    def clear(self) -> None:
        """Clear conversation history (but keep pinned messages)."""
        self._messages.clear()

    async def get_context(self) -> list[Message]:
        """
        Return the current context, trimmed to fit within token limits.
        Applies the sliding window strategy.
        """
        all_messages = self._pinned + self._messages
        token_count = await self._provider.count_tokens(all_messages)

        if token_count <= self._config.target_tokens:
            return all_messages

        # Trim: always keep pinned + last N messages, drop oldest
        logger.debug(
            f"Context trimming: {token_count} tokens → target "
            f"{self._config.target_tokens}"
        )
        kept = list(self._pinned)
        recent = self._messages[-self._config.min_recent_messages:]
        older = self._messages[:-self._config.min_recent_messages]

        # Add older messages until we hit the limit
        budget = self._config.target_tokens - await self._provider.count_tokens(
            kept + recent
        )

        for msg in reversed(older):
            msg_tokens = await self._provider.count_tokens([msg])
            if msg_tokens <= budget:
                kept.insert(len(self._pinned), msg)
                budget -= msg_tokens
            else:
                break

        return kept + recent

    @property
    def message_count(self) -> int:
        return len(self._messages)
