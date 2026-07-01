"""Unit tests for the MemoryManager (working + persistent layers)."""

from __future__ import annotations

import pytest

from jarvis.ai.providers.base import Role
from jarvis.memory.memory_manager import MemoryManager


@pytest.mark.unit
class TestMemoryManager:
    @pytest.mark.asyncio
    async def test_add_exchange_records_working_memory(self, tmp_path) -> None:
        mm = MemoryManager(db_path=str(tmp_path / "c.db"))
        await mm.initialize()
        await mm.add_exchange("hello", "hi there")

        recent = mm.recent_messages()
        assert [m.role for m in recent] == [Role.USER, Role.ASSISTANT]
        assert recent[0].content == "hello"
        assert recent[1].content == "hi there"
        await mm.close()

    @pytest.mark.asyncio
    async def test_exchange_persisted_to_history(self, tmp_path) -> None:
        mm = MemoryManager(db_path=str(tmp_path / "c.db"))
        await mm.initialize()
        assert mm.is_persistent is True
        await mm.add_exchange("remember 42", "ok")

        stored = await mm._history.get_messages(mm.session_id)
        assert [m["content"] for m in stored] == ["remember 42", "ok"]
        await mm.close()

    @pytest.mark.asyncio
    async def test_recent_messages_limit(self, tmp_path) -> None:
        mm = MemoryManager(db_path=str(tmp_path / "c.db"))
        await mm.initialize()
        for i in range(4):
            await mm.add_exchange(f"q{i}", f"a{i}")

        assert len(mm.recent_messages(2)) == 2
        assert mm.recent_messages(2)[-1].content == "a3"
        await mm.close()

    @pytest.mark.asyncio
    async def test_search_working_memory(self, tmp_path) -> None:
        mm = MemoryManager(db_path=str(tmp_path / "c.db"))
        await mm.initialize()
        await mm.add_exchange("open the terminal", "opening terminal")
        await mm.add_exchange("what's the weather", "sunny")

        results = mm.search("terminal")
        assert any("terminal" in r.content for r in results)
        await mm.close()

    @pytest.mark.asyncio
    async def test_build_context_string(self, tmp_path) -> None:
        mm = MemoryManager(db_path=str(tmp_path / "c.db"))
        await mm.initialize()
        await mm.add_exchange("hi", "hello")

        ctx = mm.build_context_string()
        assert "user: hi" in ctx
        assert "assistant: hello" in ctx
        await mm.close()
