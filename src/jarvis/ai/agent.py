"""
JARVIS Agent
============
The conversational agent: ties the :class:`ConversationEngine` together with
tool use. Explicit tool intents (e.g. "search for X", "list files in ~/Documents",
"what time is it") are detected by a small rule table and routed to a tool
deterministically — so they work even in offline mode — while everything else
defers to the conversation engine (LLM or offline responder).

When a capable LLM is connected, this layer is also the natural home for
model-driven tool calling; for now the rule table keeps tools usable without an
API key.

Usage:
    agent = JarvisAgent(engine, tools=executor)
    reply = await agent.handle("search for the tallest mountain")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from jarvis.ai.providers.base import ToolCall

if TYPE_CHECKING:
    from jarvis.ai.conversation import ConversationEngine
    from jarvis.ai.tool_executor import ToolExecutor

__all__ = ["JarvisAgent"]


@dataclass(frozen=True)
class _Rule:
    """Maps trigger phrases to a tool. ``arg`` captures the remainder into that
    parameter; ``fixed`` supplies constant parameters (e.g. a media action)."""

    tool: str
    triggers: tuple[str, ...]
    arg: str | None
    fixed: tuple[tuple[str, str], ...] = ()


# Matched against the lowercased input by prefix; first rule/trigger wins — so
# list specific phrasings before generic ones, and specific rules before broad.
_RULES: tuple[_Rule, ...] = (
    _Rule(
        "list_directory",
        ("list the files in ", "list files in ", "list directory ", "show files in ",
         "what files are in ", "what's in the folder ", "ls "),
        "path",
    ),
    _Rule(
        "read_file",
        ("read the file ", "read file ", "read me the file ", "cat "),
        "path",
    ),
    _Rule(
        "take_screenshot",
        ("take a screenshot", "take a screen shot", "take a screengrab",
         "grab a screenshot", "capture the screen", "capture my screen"),
        None,
    ),
    _Rule(
        "lock_screen",
        ("lock my screen", "lock the screen", "lock my mac", "lock my computer",
         "lock the mac", "lock screen"),
        None,
    ),
    _Rule("media_control", ("pause the music", "pause music", "pause the song",
                            "pause playback", "pause the track", "pause"),
          None, (("action", "pause"),)),
    _Rule("media_control", ("play the music", "resume the music", "resume music",
                            "resume playback", "continue the music", "start the music",
                            "play music"),
          None, (("action", "play"),)),
    _Rule("media_control", ("next song", "next track", "skip this song", "skip the song",
                            "skip song", "play the next song"),
          None, (("action", "next"),)),
    _Rule("media_control", ("previous song", "previous track", "play the previous song",
                            "go back a song", "last song"),
          None, (("action", "previous"),)),
    _Rule(
        "set_volume",
        ("set volume to ", "set the volume to ", "change volume to ",
         "turn volume to ", "volume to "),
        "level",
    ),
    _Rule("type_text", ("type out ", "type the text ", "type "), "text"),
    _Rule(
        "open_url",
        ("open website ", "open the website ", "go to the website ", "browse to ",
         "visit ", "open url "),
        "url",
    ),
    _Rule(
        "open_app",
        ("launch ", "open the app ", "open app ", "open application "),
        "name",
    ),
    _Rule(
        "search_web",
        ("search the web for ", "search for ", "web search for ", "web search ",
         "find information on ", "find info on ", "look up ", "google ", "search "),
        "query",
    ),
    _Rule(
        "open_thing",
        ("open the file ", "open file ", "open the folder ", "open folder ",
         "open my ", "open up ", "bring up ", "pull up ", "show me my ",
         "take me to my ", "go to my ", "open "),
        "target",
    ),
    _Rule(
        "system_status",
        ("system status", "system info", "cpu usage", "memory usage", "disk usage",
         "how's my system", "how is my system", "how much memory", "how much disk"),
        None,
    ),
    _Rule(
        "get_time",
        ("what time is it", "what's the time", "what is the time", "current time",
         "what day is it", "what's the date", "what is the date", "today's date"),
        None,
    ),
)

# Polite/filler wrapping that hides the real command — stripped before matching,
# so "can you please open Spotify for me" becomes "open Spotify".
_FILLER_PREFIXES = (
    "hey jarvis", "ok jarvis", "okay jarvis", "hi jarvis", "jarvis",
    "can you please", "could you please", "would you please", "can you", "could you",
    "would you", "will you", "can u", "could u", "please", "pls",
    "i want you to", "i need you to", "i'd like you to", "i would like you to",
    "go ahead and", "kindly", "just", "now",
)
_FILLER_SUFFIXES = (
    " please", " for me", " right now", " right away", " now", " thanks",
    " thank you", " pls", " quickly", " fast", " asap",
)


def _normalize(text: str) -> str:
    """Strip polite/filler wrapping so the underlying command can be matched."""
    result = text.strip().rstrip(".!").strip()
    changed = True
    while changed:
        changed = False
        low = result.lower()
        for pre in _FILLER_PREFIXES:
            if low.startswith(pre) and (len(result) == len(pre) or result[len(pre)] in " ,"):
                result = result[len(pre):].lstrip(" ,").strip()
                changed = True
                break
        low = result.lower()
        for suf in _FILLER_SUFFIXES:
            if low.endswith(suf):
                result = result[: len(result) - len(suf)].strip()
                changed = True
                break
    return result


@dataclass
class _Intent:
    tool: str
    args: dict[str, str]


class JarvisAgent:
    """Routes explicit tool intents to tools; defers everything else to chat."""

    def __init__(
        self,
        engine: ConversationEngine,
        *,
        tools: ToolExecutor | None = None,
    ) -> None:
        self._engine = engine
        self._tools = tools

    async def handle(self, user_text: str) -> str:
        """Handle one user turn — via a tool when intent is explicit, else chat."""
        intent = self._detect_intent(user_text)
        if intent is not None and self._tools is not None:
            reply = await self._run_tool(intent)
            await self._engine.memory.add_exchange(user_text, reply)
            return reply
        return await self._engine.ask(user_text)

    def _detect_intent(self, text: str) -> _Intent | None:
        text = _normalize(text)
        lowered = text.lower()
        for rule in _RULES:
            for trigger in rule.triggers:
                if not lowered.startswith(trigger):
                    continue
                args: dict[str, str] = dict(rule.fixed)
                if rule.arg is None:
                    return _Intent(tool=rule.tool, args=args)
                remainder = text[len(trigger):].strip().rstrip("?").strip()
                if remainder:
                    args[rule.arg] = remainder
                    return _Intent(tool=rule.tool, args=args)
        return None

    async def _run_tool(self, intent: _Intent) -> str:
        call = ToolCall(id=uuid.uuid4().hex[:8], name=intent.tool, arguments=intent.args)
        results = await self._tools.execute_all([call])
        result = results[0]
        if result.success:
            return str(result.output)
        logger.warning("Tool '{}' failed: {}", intent.tool, result.error)
        return f"I couldn't complete that: {result.error}"
