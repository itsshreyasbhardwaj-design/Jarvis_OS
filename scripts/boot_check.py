"""
JARVIS OS — Headless Boot Smoke Test
====================================
Starts the application, verifies core subsystems initialise and report health,
then shuts down cleanly. Exits 0 on success, 1 on failure.

This does NOT require the heavy voice/UI/native stack — it exercises the core
orchestration path (EventBus, ServiceRegistry, LifecycleManager, Settings).

Run:
    PYTHONPATH=src .venv/bin/python scripts/boot_check.py
"""

from __future__ import annotations

import asyncio
import sys


async def _main() -> int:
    from jarvis.core.application import JarvisOS

    app = JarvisOS()

    await app.start()
    print(f"[boot_check] started; state={app.state}")

    health = await app.health()
    print(f"[boot_check] health modules: {len(health)}")
    for h in health:
        print(f"  - {h['module']}: healthy={h['healthy']} {h['message']}")

    await app.stop()
    print(f"[boot_check] stopped; state={app.state}")
    print("[boot_check] OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except Exception as exc:
        print(f"[boot_check] FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)
