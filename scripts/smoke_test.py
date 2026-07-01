"""
JARVIS OS — End-to-End Smoke Test
=================================
Boots the full application, runs a conversational turn and a tool turn,
verifies the brain reports healthy, then shuts down cleanly.
Exits 0 on success, 1 on failure.

Run:
    .venv/bin/python scripts/smoke_test.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


async def _main() -> int:
    from jarvis.core.application import JarvisOS

    app = JarvisOS()
    await app.start()
    try:
        greeting = await app.ask("hello JARVIS")
        if not greeting.strip():
            raise RuntimeError("empty greeting")
        print(f"[smoke] chat   -> {greeting.splitlines()[0][:70]}")

        time_reply = await app.ask("what time is it")
        if "It is" not in time_reply:
            raise RuntimeError(f"time tool failed: {time_reply!r}")
        print(f"[smoke] tool   -> {time_reply}")

        health = await app.health()
        brain = [h for h in health if h["module"] == "ai.brain"]
        if not (brain and brain[0]["healthy"]):
            raise RuntimeError("brain module is not healthy")
        print(f"[smoke] health -> {brain[0]['message']}")

        print("[smoke] PASSED")
        return 0
    finally:
        await app.stop()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except Exception as exc:  # smoke test surfaces any boot/runtime failure
        print(f"[smoke] FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)
