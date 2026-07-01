"""
Conversation Engine
====================
The brain's spine: ties memory and the LLM router into a single ``ask()`` turn.

Each turn:
  1. Pull recent working memory as conversation context.
  2. Append the new user message.
  3. Ask the :class:`LLMRouter` for a completion (with the JARVIS system prompt).
  4. Persist the exchange via :class:`MemoryManager`.
  5. Return the assistant's reply text.

Usage:
    engine = ConversationEngine(router, memory)
    reply = await engine.ask("What's on my calendar?")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jarvis.ai.providers.base import Message, Role

if TYPE_CHECKING:
    from jarvis.ai.llm_router import LLMRouter
    from jarvis.memory.memory_manager import MemoryManager

__all__ = ["ConversationEngine", "default_system_prompt"]


def default_system_prompt() -> str:
    """A concise JARVIS persona — brief and direct, no rambling (small model)."""
    return (
        "You are JARVIS, a sharp, concise assistant on the user's Mac. Reply in one or "
        "two short sentences — no preamble, no lists, no how-to steps. Answer questions "
        "directly. You do NOT perform actions in this text reply; if the user asked you "
        "to DO something, never claim you did or will do it — instead, in one short line, "
        "tell them to say it as a plain command like 'open Safari' or 'lock my screen'. "
        "Ask for confirmation before anything destructive."
    )


class ConversationEngine:
    """
    Stateful text conversation built on memory + an LLM router.

    Usage:
        engine = ConversationEngine(router, memory)
        reply = await engine.ask("Remember that I prefer concise answers.")
    """

    def __init__(
        self,
        router: LLMRouter,
        memory: MemoryManager,
        *,
        system_prompt: str | None = None,
        max_tokens: int = 220,
        temperature: float = 0.6,
    ) -> None:
        self._router = router
        self._memory = memory
        self._system_prompt = system_prompt or default_system_prompt()
        self._max_tokens = max_tokens
        self._temperature = temperature

    @property
    def memory(self) -> MemoryManager:
        """The memory store backing this conversation (read-only access)."""
        return self._memory

    async def ask(self, user_text: str) -> str:
        """Run one conversational turn and return the assistant's reply."""
        messages = self._memory.recent_messages()
        messages.append(Message(role=Role.USER, content=user_text))

        response = await self._router.complete(
            messages,
            system_prompt=self._system_prompt,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

        await self._memory.add_exchange(user_text, response.content)
        return response.content
