"""Unit tests for the LLM router (offline fallback + live-path routing)."""

from __future__ import annotations

import pytest

from jarvis.ai.llm_router import LLMRouter
from jarvis.ai.providers.base import AIResponse, Message, Role


def _user(text: str) -> Message:
    return Message(role=Role.USER, content=text)


@pytest.mark.unit
class TestLLMRouterOffline:
    @pytest.mark.asyncio
    async def test_offline_returns_airesponse(self) -> None:
        router = LLMRouter(offline_only=True)
        resp = await router.complete([_user("hello")])
        assert isinstance(resp, AIResponse)
        assert resp.provider == "offline"
        assert resp.content

    @pytest.mark.asyncio
    async def test_offline_greeting(self) -> None:
        router = LLMRouter(offline_only=True)
        resp = await router.complete([_user("hi")])
        assert "JARVIS" in resp.content

    @pytest.mark.asyncio
    async def test_offline_recalls_prior_user_message(self) -> None:
        router = LLMRouter(offline_only=True)
        messages = [
            _user("my name is Shrey"),
            Message(role=Role.ASSISTANT, content="Noted."),
            _user("what did I say?"),
        ]
        resp = await router.complete(messages)
        assert "Shrey" in resp.content

    def test_is_live_false_without_litellm_or_key(self) -> None:
        # Test environment has neither litellm installed nor an API key set.
        assert LLMRouter().is_live() is False

    def test_offline_only_is_never_live(self) -> None:
        assert LLMRouter(offline_only=True).is_live() is False


@pytest.mark.unit
class TestLLMRouterLivePath:
    @pytest.mark.asyncio
    async def test_live_backend_is_used_when_ready(self, monkeypatch) -> None:
        router = LLMRouter(models=["anthropic/claude-sonnet-5"])
        monkeypatch.setattr(router, "_litellm_ready", lambda: True)

        async def fake_complete(model, messages, system_prompt, max_tokens, temperature):
            return AIResponse(content="LIVE", model=model, provider="litellm")

        monkeypatch.setattr(router, "_complete_litellm", fake_complete)

        resp = await router.complete([_user("hi")])
        assert resp.content == "LIVE"
        assert resp.provider == "litellm"

    @pytest.mark.asyncio
    async def test_fallback_chain_tries_next_model(self, monkeypatch) -> None:
        router = LLMRouter(models=["bad-model", "good-model"])
        monkeypatch.setattr(router, "_litellm_ready", lambda: True)
        seen: list[str] = []

        async def fake_complete(model, messages, system_prompt, max_tokens, temperature):
            seen.append(model)
            if model == "bad-model":
                raise RuntimeError("model unavailable")
            return AIResponse(content="ok", model=model, provider="litellm")

        monkeypatch.setattr(router, "_complete_litellm", fake_complete)

        resp = await router.complete([_user("hi")])
        assert seen == ["bad-model", "good-model"]
        assert resp.content == "ok"

    @pytest.mark.asyncio
    async def test_all_live_models_fail_falls_back_offline(self, monkeypatch) -> None:
        router = LLMRouter(models=["m1", "m2"])
        monkeypatch.setattr(router, "_litellm_ready", lambda: True)

        async def boom(*args, **kwargs):
            raise RuntimeError("api down")

        monkeypatch.setattr(router, "_complete_litellm", boom)

        resp = await router.complete([_user("hi")])
        assert resp.provider == "offline"

    def test_settings_model_prepended_to_chain(self) -> None:
        class _AI:
            model = "claude-opus-4-8"

        class _Settings:
            ai = _AI()

        router = LLMRouter(_Settings())
        assert router.models[0] == "anthropic/claude-opus-4-8"
