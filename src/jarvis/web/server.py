"""
JARVIS Web Console — Backend
============================
A local FastAPI app that serves the browser UI and runs the JARVIS brain.

Endpoints:
  GET  /            → the console UI (voice + chat + two-clap wake)
  GET  /api/status  → {"live": bool, "model": str}
  POST /api/chat    → {"text": ...} → {"reply": ..., "live": bool}

The browser handles microphone, speech-to-text, text-to-speech, and clap
detection with built-in Web APIs; this backend handles reasoning and Mac
control. Run it via ``jarvis console`` (see cli.py).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["app", "create_app"]

_STATIC = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    text: str


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    from dotenv import load_dotenv

    from jarvis.ai.agent import JarvisAgent
    from jarvis.ai.conversation import ConversationEngine
    from jarvis.ai.llm_router import LLMRouter
    from jarvis.ai.tools import build_tool_executor
    from jarvis.config.settings import Settings
    from jarvis.desktop.permissions import PermissionManager
    from jarvis.integrations.web_search import WebSearch
    from jarvis.memory.memory_manager import MemoryManager

    load_dotenv()
    settings = Settings()
    memory = MemoryManager(settings)
    await memory.initialize(title="JARVIS Console")
    router = LLMRouter(settings)
    tools = build_tool_executor(
        web_search=WebSearch(),
        permissions=PermissionManager(require_confirmation=False, safe_mode=False),
    )
    engine = ConversationEngine(router, memory)

    app.state.agent = JarvisAgent(engine, tools=tools)
    app.state.router = router
    app.state.memory = memory
    try:
        yield
    finally:
        await memory.close()


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="JARVIS Console", lifespan=_lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return (_STATIC / "index.html").read_text(encoding="utf-8")

    @app.get("/api/status")
    async def status() -> dict[str, object]:
        router = app.state.router
        return {"live": router.is_live(), "model": router.active_backend()}

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, object]:
        reply = await app.state.agent.handle(request.text)
        return {"reply": reply, "live": app.state.router.is_live()}

    return app


app = create_app()
