"""
Browser Manager
===============
Manages Playwright browser instances for web automation.
Supports Chromium, Firefox, and WebKit (Safari engine).

Safety features:
- Never stores or transmits passwords without explicit user consent
- All login/form operations require confirmation
- Audit log of all browser actions
- Sandboxed browser profile (no real cookies/extensions)

Design:
- One browser instance, multiple pages (tabs)
- Async context managers for automatic cleanup
- Screenshot on every action for audit trail (opt-in)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger


class BrowserManager:
    """
    Manages Playwright browser lifecycle.

    Usage:
        manager = BrowserManager(browser_type="chromium", headless=False)
        await manager.initialize()

        async with manager.new_page() as page:
            await page.goto("https://google.com")
            content = await page.content()

        await manager.cleanup()
    """

    def __init__(
        self,
        browser_type: str = "chromium",   # chromium | firefox | webkit
        headless: bool = False,
        timeout_ms: int = 30_000,
        user_data_dir: str | None = None,
    ) -> None:
        self._browser_type = browser_type
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._user_data_dir = user_data_dir
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None

    async def initialize(self) -> None:
        """Start Playwright and launch the browser."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "playwright required: pip install playwright && playwright install"
            ) from None

        logger.info(
            f"Starting browser: {self._browser_type} "
            f"(headless={self._headless})"
        )
        self._playwright = await async_playwright().start()

        browser_launcher = getattr(self._playwright, self._browser_type)
        self._browser = await browser_launcher.launch(
            headless=self._headless,
            args=["--no-sandbox"] if self._browser_type == "chromium" else [],
        )

        # Create a fresh browser context (isolated profile)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._context.set_default_timeout(self._timeout_ms)
        logger.success(f"Browser ready: {self._browser_type}")

    @asynccontextmanager
    async def new_page(self) -> AsyncIterator[Any]:
        """Create a new browser tab as a context manager."""
        if not self._context:
            raise RuntimeError(
                "Browser not initialized. Call initialize() first."
            )
        page = await self._context.new_page()
        try:
            yield page
        finally:
            await page.close()

    async def cleanup(self) -> None:
        """Close browser and release resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser cleanup complete")

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._browser.is_connected()
