"""Integration test: the booted JarvisOS app can converse via its brain."""

from __future__ import annotations

import pytest

from jarvis.core.application import JarvisOS


@pytest.mark.unit
class TestApplicationAsk:
    @pytest.mark.asyncio
    async def test_booted_app_converses_and_reports_brain_health(
        self, monkeypatch, tmp_path
    ) -> None:
        # Persistent memory writes under cwd/data — keep it in a temp dir.
        monkeypatch.chdir(tmp_path)
        app = JarvisOS()
        await app.start()
        try:
            reply = await app.ask("hello")
            assert isinstance(reply, str)
            assert reply

            health = await app.health()
            assert any(h["module"] == "ai.brain" and h["healthy"] for h in health)
        finally:
            await app.stop()

    @pytest.mark.asyncio
    async def test_ask_before_start_raises(self) -> None:
        app = JarvisOS()
        with pytest.raises(RuntimeError):
            await app.ask("hi")
