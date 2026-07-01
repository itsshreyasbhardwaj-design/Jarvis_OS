"""Unit tests for macOS desktop control (open / AppleScript)."""

from __future__ import annotations

import pytest

from jarvis.integrations.desktop_control import ControlResult, DesktopControl


@pytest.mark.unit
class TestDesktopControl:
    @pytest.mark.asyncio
    async def test_open_url_normalizes_bare_domain(self, monkeypatch) -> None:
        captured: dict = {}

        async def fake_run(cmd, _msg):
            captured["cmd"] = cmd
            return ControlResult(success=True, output="ok")

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.open_url("apple.com")
        assert captured["cmd"] == ["open", "https://apple.com"]

    @pytest.mark.asyncio
    async def test_open_url_keeps_full_url(self, monkeypatch) -> None:
        captured: dict = {}

        async def fake_run(cmd, _msg):
            captured["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.open_url("https://example.com/page")
        assert captured["cmd"] == ["open", "https://example.com/page"]

    @pytest.mark.asyncio
    async def test_open_app_uses_open_dash_a(self, monkeypatch) -> None:
        captured: dict = {}

        async def fake_run(cmd, _msg):
            captured["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.open_app("Safari")
        assert captured["cmd"] == ["open", "-a", "Safari"]

    @pytest.mark.asyncio
    async def test_set_volume_clamps_and_scripts(self, monkeypatch) -> None:
        captured: dict = {}

        async def fake_run(cmd, _msg):
            captured["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.set_volume(150)  # clamps to 100
        assert captured["cmd"] == ["osascript", "-e", "set volume output volume 100"]

    @pytest.mark.asyncio
    async def test_type_text_escapes_quotes(self, monkeypatch) -> None:
        captured: dict = {}

        async def fake_run(cmd, _msg):
            captured["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.type_text('say "hi"')
        assert '\\"hi\\"' in captured["cmd"][2]

    @pytest.mark.asyncio
    async def test_run_applescript_live(self) -> None:
        # Real osascript — benign and deterministic (no UI side effects).
        ctrl = DesktopControl()
        result = await ctrl.run_applescript('return "hello from applescript"')
        assert result.success
        assert "hello from applescript" in result.output

    @pytest.mark.asyncio
    async def test_open_folder_maps_name_to_path(self, monkeypatch) -> None:
        cap: dict = {}

        async def fake_run(cmd, _msg):
            cap["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.open_folder("downloads")
        assert cap["cmd"][0] == "open"
        assert cap["cmd"][1].endswith("/Downloads")

    @pytest.mark.asyncio
    async def test_open_smart_dispatches(self, monkeypatch) -> None:
        seen: list = []

        async def folder(name):
            seen.append(("folder", name))
            return ControlResult(success=True)

        async def url(u):
            seen.append(("url", u))
            return ControlResult(success=True)

        async def app(a):
            seen.append(("app", a))
            return ControlResult(success=True)

        async def path(p):
            seen.append(("path", p))
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "open_folder", folder)
        monkeypatch.setattr(ctrl, "open_url", url)
        monkeypatch.setattr(ctrl, "open_app", app)
        monkeypatch.setattr(ctrl, "open_path", path)
        await ctrl.open_smart("Downloads")
        await ctrl.open_smart("apple.com")
        await ctrl.open_smart("Spotify")
        await ctrl.open_smart("~/notes.txt")
        await ctrl.open_smart("music")
        await ctrl.open_smart("my downloads")
        assert ("folder", "downloads") in seen
        assert ("url", "apple.com") in seen
        assert ("app", "Spotify") in seen
        assert ("path", "~/notes.txt") in seen
        assert ("app", "Music") in seen  # alias → app, not the ~/Music folder
        assert ("folder", "downloads") in seen  # "my downloads" → folder

    @pytest.mark.asyncio
    async def test_lock_screen_command(self, monkeypatch) -> None:
        cap: dict = {}

        async def fake_run(cmd, _msg):
            cap["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.lock_screen()
        assert cap["cmd"] == ["pmset", "displaysleepnow"]

    @pytest.mark.asyncio
    async def test_take_screenshot_command(self, monkeypatch) -> None:
        cap: dict = {}

        async def fake_run(cmd, _msg):
            cap["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.take_screenshot()
        assert cap["cmd"][0] == "screencapture"
        assert cap["cmd"][-1].endswith(".png")

    @pytest.mark.asyncio
    async def test_media_control_targets_players(self, monkeypatch) -> None:
        cap: dict = {}

        async def fake_run(cmd, _msg):
            cap["cmd"] = cmd
            return ControlResult(success=True)

        ctrl = DesktopControl()
        monkeypatch.setattr(ctrl, "_run", fake_run)
        await ctrl.media_control("next")
        assert cap["cmd"][0] == "osascript"
        assert "next track" in cap["cmd"][2]
