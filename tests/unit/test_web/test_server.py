"""Integration test for the JARVIS web console backend."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from jarvis.web.server import app


@pytest.mark.unit
class TestWebConsole:
    def test_status_chat_and_ui(self, monkeypatch, tmp_path) -> None:
        # Persistent memory writes under cwd/data — keep it in a temp dir.
        monkeypatch.chdir(tmp_path)
        with TestClient(app) as client:
            status = client.get("/api/status")
            assert status.status_code == 200
            assert "live" in status.json()

            chat = client.post("/api/chat", json={"text": "hello"})
            assert chat.status_code == 200
            assert chat.json()["reply"]

            tool = client.post("/api/chat", json={"text": "what time is it"})
            assert "It is" in tool.json()["reply"]

            ui = client.get("/")
            assert ui.status_code == 200
            assert "JARVIS" in ui.text
