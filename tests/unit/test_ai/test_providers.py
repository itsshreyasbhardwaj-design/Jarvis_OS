"""Unit tests for AI provider abstraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from jarvis.ai.providers.base import (
    AIProvider,
    AIResponse,
    Message,
    Role,
    TokenUsage,
)


@pytest.mark.unit
class TestAIProviderBase:
    """Tests for the AI provider abstraction."""

    def test_message_creation(self) -> None:
        msg = Message(role=Role.USER, content="Hello JARVIS")
        assert msg.role == Role.USER
        assert msg.content == "Hello JARVIS"

    def test_token_usage_total(self) -> None:
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_ai_response_has_tool_calls(self) -> None:
        from jarvis.ai.providers.base import ToolCall
        response = AIResponse(
            content="",
            model="test",
            provider="test",
            tool_calls=[ToolCall(id="1", name="search", arguments={})],
        )
        assert response.has_tool_calls is True

    def test_jarvis_system_prompt_contains_key_principles(
        self, mock_ai_provider: AIProvider
    ) -> None:
        prompt = mock_ai_provider.build_jarvis_system_prompt()
        assert "confirmation" in prompt.lower() or "JARVIS" in prompt

    @pytest.mark.asyncio
    async def test_mock_provider_complete(self, mock_ai_provider: AIProvider) -> None:
        """Mock provider returns expected response."""
        messages = [Message(role=Role.USER, content="Hello")]
        response = await mock_ai_provider.complete(messages)

        assert isinstance(response, AIResponse)
        assert response.content
        assert response.model == "mock-model"

    @pytest.mark.asyncio
    async def test_mock_provider_health_check(
        self, mock_ai_provider: AIProvider
    ) -> None:
        result = await mock_ai_provider.health_check()
        assert result is True
