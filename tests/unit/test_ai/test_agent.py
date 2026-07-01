"""Unit tests for the JarvisAgent (intent routing + tool/chat dispatch)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from jarvis.ai.agent import JarvisAgent
from jarvis.ai.tool_executor import ToolResult


class _FakeMemory:
    def __init__(self) -> None:
        self.exchanges: list[tuple[str, str]] = []

    async def add_exchange(self, user: str, assistant: str) -> None:
        self.exchanges.append((user, assistant))


class _FakeEngine:
    def __init__(self) -> None:
        self.memory = _FakeMemory()
        self.asked: list[str] = []

    async def ask(self, text: str) -> str:
        self.asked.append(text)
        return f"chat:{text}"


def _tools_returning(result: ToolResult) -> AsyncMock:
    tools = AsyncMock()
    tools.execute_all = AsyncMock(return_value=[result])
    return tools


@pytest.mark.unit
class TestJarvisAgent:
    @pytest.mark.asyncio
    async def test_non_tool_input_defers_to_engine(self) -> None:
        engine = _FakeEngine()
        agent = JarvisAgent(engine, tools=None)
        reply = await agent.handle("how are you")
        assert reply == "chat:how are you"
        assert engine.asked == ["how are you"]

    @pytest.mark.asyncio
    async def test_search_intent_routes_to_tool(self) -> None:
        engine = _FakeEngine()
        tools = _tools_returning(
            ToolResult(tool_call_id="1", tool_name="search_web", success=True, output="RESULTS")
        )
        agent = JarvisAgent(engine, tools=tools)

        reply = await agent.handle("search for dune")

        assert reply == "RESULTS"
        call = tools.execute_all.call_args.args[0][0]
        assert call.name == "search_web"
        assert call.arguments == {"query": "dune"}
        assert engine.memory.exchanges == [("search for dune", "RESULTS")]
        assert engine.asked == []  # bypassed the LLM

    @pytest.mark.asyncio
    async def test_tool_failure_yields_friendly_message(self) -> None:
        engine = _FakeEngine()
        tools = _tools_returning(
            ToolResult(tool_call_id="1", tool_name="search_web", success=False, error="boom")
        )
        agent = JarvisAgent(engine, tools=tools)
        reply = await agent.handle("look up dune")
        assert "couldn't complete" in reply.lower()

    @pytest.mark.asyncio
    async def test_routes_no_arg_tool(self) -> None:
        engine = _FakeEngine()
        tools = _tools_returning(
            ToolResult(tool_call_id="1", tool_name="get_time", success=True, output="It is noon")
        )
        agent = JarvisAgent(engine, tools=tools)
        reply = await agent.handle("what time is it")
        assert reply == "It is noon"
        call = tools.execute_all.call_args.args[0][0]
        assert call.name == "get_time"
        assert call.arguments == {}

    def test_intent_detection(self) -> None:
        agent = JarvisAgent(_FakeEngine(), tools=AsyncMock())
        detect = agent._detect_intent

        assert detect("search for cats").args == {"query": "cats"}
        assert detect("search cats").args == {"query": "cats"}
        assert detect("look up the weather?").args == {"query": "the weather"}

        list_intent = detect("list files in /tmp")
        assert list_intent.tool == "list_directory"
        assert list_intent.args == {"path": "/tmp"}

        read_intent = detect("read file /tmp/notes.txt")
        assert read_intent.tool == "read_file"
        assert read_intent.args == {"path": "/tmp/notes.txt"}

        launch_intent = detect("launch Spotify")
        assert launch_intent.tool == "open_app"
        assert launch_intent.args == {"name": "Spotify"}

        url_intent = detect("open website apple.com")
        assert url_intent.tool == "open_url"
        assert url_intent.args == {"url": "apple.com"}

        vol_intent = detect("set volume to 40")
        assert vol_intent.tool == "set_volume"
        assert vol_intent.args == {"level": "40"}

        type_intent = detect("type hello world")
        assert type_intent.tool == "type_text"
        assert type_intent.args == {"text": "hello world"}

        assert detect("take a screenshot").tool == "take_screenshot"
        assert detect("lock my screen").tool == "lock_screen"

        pause = detect("pause the music")
        assert pause.tool == "media_control"
        assert pause.args == {"action": "pause"}

        nxt = detect("next song")
        assert nxt.tool == "media_control"
        assert nxt.args == {"action": "next"}

        openf = detect("open my downloads")
        assert openf.tool == "open_thing"
        assert openf.args == {"target": "downloads"}

        opena = detect("open Spotify")
        assert opena.tool == "open_thing"
        assert opena.args == {"target": "Spotify"}

        assert detect("what time is it").tool == "get_time"
        assert detect("system status").tool == "system_status"
        assert detect("hello there") is None

    def test_polite_and_filler_still_route(self) -> None:
        agent = JarvisAgent(_FakeEngine(), tools=AsyncMock())
        detect = agent._detect_intent

        assert detect("please open Spotify").tool == "open_thing"
        assert detect("can you lock my screen").tool == "lock_screen"
        assert detect("hey JARVIS, take a screenshot").tool == "take_screenshot"

        vol = detect("could you set the volume to 20 for me")
        assert vol.tool == "set_volume"
        assert vol.args == {"level": "20"}

        opn = detect("open up my downloads please")
        assert opn.tool == "open_thing"
        assert opn.args == {"target": "my downloads"}
