"""
LLM Router
==========
Routes chat completions to the best available backend and returns the
project-standard :class:`AIResponse`.

Order of preference:
  1. ``litellm.acompletion`` against a configured model + fallback chain —
     used only when ``litellm`` is importable AND an API key is present.
     On a per-model failure it falls through to the next model in the chain.
  2. A built-in offline responder, so JARVIS always replies even with no
     network, no API key, and none of the heavy optional dependencies
     installed. This keeps the assistant demoable and fully testable.

Adding real intelligence is zero-code: set ``ANTHROPIC_API_KEY`` (or
``OPENAI_API_KEY`` / ``GEMINI_API_KEY``) and ``uv pip install litellm``.

Usage:
    router = LLMRouter(settings)
    resp = await router.complete([Message(role=Role.USER, content="hi")])
    print(resp.content)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import time
from typing import TYPE_CHECKING

from loguru import logger

from jarvis.ai.providers.base import AIResponse, Message, Role, TokenUsage

if TYPE_CHECKING:
    from collections.abc import Sequence

    from jarvis.config.settings import Settings

__all__ = ["LLMRouter", "LLMRouterError"]

# Current Anthropic model identifiers (litellm "anthropic/<model>" form).
# Priority mirrors the design doc: most capable first, cheapest last.
DEFAULT_MODELS: tuple[str, ...] = (
    "anthropic/claude-opus-4-8",
    "anthropic/claude-sonnet-5",
    "anthropic/claude-haiku-4-5-20251001",
)

_GREETINGS = ("hi", "hello", "hey", "yo", "good morning", "good evening", "good afternoon")
# Maps a litellm provider prefix to the env var litellm reads its key from.
_PROVIDER_KEY_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "vertex_ai": "GOOGLE_API_KEY",
}


class LLMRouterError(RuntimeError):
    """Raised when no backend (live or offline) can produce a response."""


# Local Apple-Silicon model (MLX) — real LLM intelligence with no API key.
LOCAL_MODEL = os.environ.get("JARVIS_LOCAL_MODEL", "mlx-community/Llama-3.2-1B-Instruct-4bit")


class _MLX:
    """Lazily-loaded local MLX model. One shared instance per process."""

    _loaded = False
    _ok = False
    _model = None
    _tok = None
    _pool: concurrent.futures.ThreadPoolExecutor | None = None

    @staticmethod
    def _importable() -> bool:
        try:
            import mlx_lm  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def _model_cached() -> bool:
        from pathlib import Path

        snaps = (
            Path.home()
            / ".cache/huggingface/hub"
            / ("models--" + LOCAL_MODEL.replace("/", "--"))
            / "snapshots"
        )
        if not snaps.exists():
            return False
        return any(any(s.glob("*.safetensors")) for s in snaps.iterdir())

    @classmethod
    def available(cls) -> bool:
        """Cheap check (no model load): importable and weights on disk."""
        if cls._loaded:
            return cls._ok
        return cls._importable() and cls._model_cached()

    @classmethod
    def _ensure_loaded(cls) -> bool:
        if cls._loaded:
            return cls._ok
        cls._loaded = True
        try:
            from mlx_lm import load

            cls._model, cls._tok = load(LOCAL_MODEL)
            cls._ok = True
            logger.info("Local MLX model loaded: {}", LOCAL_MODEL)
        except Exception as exc:  # model missing / OOM — degrade to offline
            logger.warning("MLX model load failed: {}", exc)
            cls._ok = False
        return cls._ok

    @classmethod
    def _executor(cls) -> concurrent.futures.ThreadPoolExecutor:
        if cls._pool is None:
            cls._pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="mlx"
            )
        return cls._pool

    @classmethod
    async def complete(
        cls, messages: list[Message], system_prompt: str | None, max_tokens: int
    ) -> AIResponse:
        # MLX's Metal stream is thread-local, so load AND generate must run on
        # the SAME thread — a dedicated single-worker executor guarantees that
        # while keeping the event loop unblocked.
        loop = asyncio.get_event_loop()
        if not await loop.run_in_executor(cls._executor(), cls._ensure_loaded):
            raise LLMRouterError("MLX model unavailable")

        def _generate() -> str:
            from mlx_lm import generate

            chat: list[dict[str, str]] = []
            if system_prompt:
                chat.append({"role": "system", "content": system_prompt})
            for msg in messages:
                role = msg.role.value if isinstance(msg.role, Role) else str(msg.role)
                chat.append({"role": role, "content": msg.content})
            prompt = cls._tok.apply_chat_template(
                chat, add_generation_prompt=True, tokenize=False
            )
            return generate(
                cls._model, cls._tok, prompt=prompt, max_tokens=max_tokens, verbose=False
            )

        start = time.perf_counter()
        text = await loop.run_in_executor(cls._executor(), _generate)
        return AIResponse(
            content=text.strip(),
            model=LOCAL_MODEL.split("/")[-1],
            provider="mlx",
            response_time_ms=(time.perf_counter() - start) * 1000,
        )


class LLMRouter:
    """
    Provider-agnostic chat completion router with graceful offline fallback.

    Usage:
        router = LLMRouter(settings)
        if router.is_live():
            ...  # real model calls
        resp = await router.complete(messages, system_prompt="You are JARVIS.")
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        models: Sequence[str] | None = None,
        offline_only: bool = False,
    ) -> None:
        self._settings = settings
        self._offline_only = offline_only
        if models is not None:
            self._models: list[str] = list(models)
        elif settings is not None:
            self._models = self._models_from_settings(settings)
        else:
            self._models = list(DEFAULT_MODELS)

    # --- Public API ---

    def is_live(self) -> bool:
        """True if a real LLM backend (cloud key or local MLX model) is usable."""
        return self._litellm_ready() or (not self._offline_only and _MLX.available())

    def active_backend(self) -> str:
        """Label for the current brain: a cloud model, the local model, or offline."""
        if self._litellm_ready():
            return self._models[0]
        if not self._offline_only and _MLX.available():
            return f"local · {LOCAL_MODEL.split('/')[-1]}"
        return "offline"

    @property
    def models(self) -> list[str]:
        """The configured model fallback chain."""
        return list(self._models)

    async def complete(
        self,
        messages: list[Message],
        *,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> AIResponse:
        """
        Produce a completion for ``messages``.

        Tries the live model chain (when available), then falls back to the
        offline responder. Never raises for ordinary backend failures.
        """
        if self._litellm_ready():
            chain = [model] if model else self._models
            for candidate in chain:
                try:
                    return await self._complete_litellm(
                        candidate, messages, system_prompt, max_tokens, temperature
                    )
                except Exception as exc:  # surface to next model, then offline
                    logger.warning("LLM model '{}' failed: {}", candidate, exc)
                    continue
            logger.warning("All cloud models failed; trying local model")
        if not self._offline_only and _MLX.available():
            try:
                return await _MLX.complete(messages, system_prompt, max_tokens)
            except Exception as exc:  # local model failed — fall back to offline
                logger.warning("Local model failed: {}", exc)
        return self._complete_offline(messages)

    # --- Live backend (litellm) ---

    def _litellm_ready(self) -> bool:
        if self._offline_only:
            return False
        try:
            import litellm  # noqa: F401
        except ImportError:
            return False
        return self._has_api_key()

    def _has_api_key(self) -> bool:
        # Only the key for the PRIMARY model's provider counts — a stray key for
        # some other provider must not flip JARVIS into "live" mode and then fail.
        first = self._models[0] if self._models else ""
        provider = first.split("/", 1)[0] if "/" in first else "anthropic"
        var = _PROVIDER_KEY_VARS.get(provider)
        return bool(var and os.environ.get(var))

    async def _complete_litellm(
        self,
        model: str,
        messages: list[Message],
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        import litellm

        payload = self._to_litellm_messages(messages, system_prompt)
        start = time.perf_counter()
        response = await litellm.acompletion(
            model=model,
            messages=payload,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        choice = response.choices[0]
        content = getattr(choice.message, "content", "") or ""
        usage = getattr(response, "usage", None)
        return AIResponse(
            content=content,
            model=model,
            provider="litellm",
            usage=TokenUsage(
                input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            ),
            finish_reason=getattr(choice, "finish_reason", "stop") or "stop",
            response_time_ms=elapsed_ms,
        )

    @staticmethod
    def _to_litellm_messages(
        messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        if system_prompt:
            payload.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.role.value if isinstance(msg.role, Role) else str(msg.role)
            payload.append({"role": role, "content": msg.content})
        return payload

    def _models_from_settings(self, settings: Settings) -> list[str]:
        chain = list(DEFAULT_MODELS)
        configured = getattr(getattr(settings, "ai", None), "model", "") or ""
        if configured:
            model = configured if "/" in configured else f"anthropic/{configured}"
            chain = [model, *[m for m in chain if m != model]]
        return chain

    # --- Offline backend (always available) ---

    def _complete_offline(self, messages: list[Message]) -> AIResponse:
        user_messages = [m for m in messages if m.role == Role.USER]
        last = user_messages[-1].content.strip() if user_messages else ""
        lowered = last.lower()
        prior = [m.content for m in user_messages[:-1]]

        if not last:
            reply = "I'm here. What can I do for you?"
        elif any(lowered == g or lowered.startswith(g + " ") for g in _GREETINGS):
            reply = "Hello — JARVIS here. I'm running in offline mode, but I'm listening."
        elif (
            "what did i" in lowered
            or "what i said" in lowered
            or "repeat" in lowered
            or ("remember" in lowered and "?" in lowered)
        ):
            reply = (
                f'You said: "{prior[-1]}".'
                if prior
                else "We haven't exchanged anything yet this session."
            )
        elif "your name" in lowered or "who are you" in lowered:
            reply = "I'm JARVIS, your AI desktop assistant."
        elif lowered.endswith("?"):
            reply = (
                f'Good question — but in offline mode I can\'t reason about "{last}" yet. '
                "Add an API key to unlock full answers."
            )
        else:
            reply = f'Noted: "{last}".'

        return AIResponse(
            content=reply, model="offline", provider="offline", finish_reason="stop"
        )
