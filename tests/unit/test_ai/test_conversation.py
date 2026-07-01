"""Unit tests for the ConversationEngine (memory + router integration)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from jarvis.ai.conversation import ConversationEngine, default_system_prompt
from jarvis.ai.providers.base import AIResponse
from jarvis.memory.memory_manager import MemoryManager


async def _memory(tmp_path):
    mm = MemoryManager(db_path=str(tmp_path / "c.db"))
    await mm.initialize()
    return mm


def _router_returning(text: str) -> AsyncMock:
    router = AsyncMock()
    router.complete = AsyncMock(
        return_value=AIResponse(content=text, model="x", provider="offline")
    )
    return router


@pytest.mark.unit
class TestConversationEngine:
    def test_default_system_prompt_mentions_jarvis(self) -> None:
        prompt = default_system_prompt()
        assert "JARVIS" in prompt
        assert "confirmation" in prompt.lower()

    @pytest.mark.asyncio
    async def test_ask_returns_reply_and_updates_memory(self, tmp_path) -> None:
        mm = await _memory(tmp_path)
        router = _router_returning("Hello Shrey")
        engine = ConversationEngine(router, mm)

        reply = await engine.ask("hi")

        assert reply == "Hello Shrey"
        recent = mm.recent_messages()
        assert recent[-2].content == "hi"          # user turn
        assert recent[-1].content == "Hello Shrey"  # assistant turn
        await mm.close()

    @pytest.mark.asyncio
    async def test_router_receives_user_message_and_system_prompt(self, tmp_path) -> None:
        mm = await _memory(tmp_path)
        router = _router_returning("ok")
        engine = ConversationEngine(router, mm)

        await engine.ask("hello")

        sent_messages = router.complete.call_args.args[0]
        assert sent_messages[-1].content == "hello"
        assert "JARVIS" in router.complete.call_args.kwargs["system_prompt"]
        await mm.close()

    @pytest.mark.asyncio
    async def test_prior_turns_included_as_context(self, tmp_path) -> None:
        mm = await _memory(tmp_path)
        router = _router_returning("ok")
        engine = ConversationEngine(router, mm)

        await engine.ask("first")
        await engine.ask("second")

        sent_messages = router.complete.call_args.args[0]
        contents = [m.content for m in sent_messages]
        assert "first" in contents          # prior user turn carried forward
        assert contents[-1] == "second"     # current turn last
        await mm.close()
