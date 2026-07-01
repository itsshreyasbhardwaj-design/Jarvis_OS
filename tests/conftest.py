"""
JARVIS OS — Pytest Configuration
==================================
Shared fixtures available to all tests.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from jarvis.config.settings import Settings
from jarvis.core.event_bus import EventBus
from jarvis.core.service_registry import ServiceRegistry

# ---------------------------------------------------------------------------
# Event Loop (required for pytest-asyncio)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Core Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_local_model(monkeypatch):
    """Never load the multi-GB local MLX model during tests (keep them fast)."""
    monkeypatch.setattr("jarvis.ai.llm_router._MLX.available", lambda: False)


@pytest.fixture
async def event_bus() -> AsyncGenerator[EventBus, None]:
    """Provide a fresh, started EventBus for each test."""
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def service_registry() -> ServiceRegistry:
    """Provide a fresh ServiceRegistry for each test."""
    return ServiceRegistry()


@pytest.fixture
def test_settings() -> Settings:
    """Settings configured for testing (no external API calls)."""
    return Settings(
        _env_file=None,  # Don't load .env in tests
        JARVIS_ENV="testing",
        JARVIS_LOG_LEVEL="WARNING",
    )


# ---------------------------------------------------------------------------
# AI Provider Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ai_provider():
    """Mock AI provider that returns predictable responses."""
    from jarvis.ai.providers.base import AIProvider, AIResponse, TokenUsage

    provider = MagicMock(spec=AIProvider)
    provider.provider_name = "mock"
    provider.model_name = "mock-model"
    provider.max_context_tokens = 4096

    provider.complete = AsyncMock(return_value=AIResponse(
        content="I am JARVIS, your AI assistant.",
        model="mock-model",
        provider="mock",
        usage=TokenUsage(input_tokens=10, output_tokens=20),
    ))
    provider.count_tokens = AsyncMock(return_value=42)
    provider.health_check = AsyncMock(return_value=True)
    # Bind the real base implementation so prompt-content assertions are meaningful
    # (the method ignores instance state, so passing the mock as self is safe).
    provider.build_jarvis_system_prompt = lambda: AIProvider.build_jarvis_system_prompt(provider)
    return provider


# ---------------------------------------------------------------------------
# Memory Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def short_term_memory():
    """Fresh short-term memory for testing."""
    from jarvis.memory.short_term import ShortTermMemory
    return ShortTermMemory(max_entries=10)


@pytest.fixture
async def long_term_memory(tmp_path):
    """Long-term memory backed by a temp SQLite database."""
    from jarvis.memory.long_term import LongTermMemory
    db_path = str(tmp_path / "test_memory.db")
    mem = LongTermMemory(db_path=db_path)
    await mem.initialize()
    yield mem
    await mem.close()


# ---------------------------------------------------------------------------
# Security Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def permissive_permissions():
    """Permission manager that auto-approves everything (for testing non-security code)."""
    from jarvis.desktop.permissions import PermissionManager

    async def auto_approve(request):
        return True

    return PermissionManager(
        require_confirmation=False,
        safe_mode=False,
        confirmation_callback=auto_approve,
    )


@pytest.fixture
def restricted_permissions():
    """Permission manager in safe mode (for testing permission enforcement)."""
    from jarvis.desktop.permissions import PermissionManager
    return PermissionManager(require_confirmation=True, safe_mode=True)


# ---------------------------------------------------------------------------
# File System Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_workspace(tmp_path):
    """A temporary directory with sample files for file system tests."""
    # Create sample file structure
    docs = tmp_path / "documents"
    docs.mkdir()
    (docs / "report.txt").write_text("This is a test report.")
    (docs / "data.csv").write_text("name,value\nfoo,1\nbar,2")

    code = tmp_path / "code"
    code.mkdir()
    (code / "main.py").write_text("print('hello jarvis')")

    return tmp_path
