"""
Content Extractor
=================
Extracts structured information from web pages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from jarvis.browser.browser_manager import BrowserManager


@dataclass
class PageContent:
    """Extracted content from a web page."""
    url: str
    title: str
    text: str
    links: list[dict[str, str]] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ContentExtractor:
    """
    Extracts clean content from web pages.

    Usage:
        extractor = ContentExtractor(browser_manager)
        content = await extractor.extract("https://example.com")
        print(content.title)
        print(content.text[:500])
    """

    def __init__(self, browser_manager: BrowserManager) -> None:
        self._browser = browser_manager

    async def extract(
        self,
        url: str,
        *,
        extract_links: bool = False,
        extract_images: bool = False,
    ) -> PageContent:
        """Extract structured content from a URL."""
        logger.info(f"Extracting: {url}")
        async with self._browser.new_page() as page:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")

            title = await page.title()
            text = await page.evaluate("""
                () => {
                    const tags = ["script", "style", "nav", "footer", "header",
                                  "aside", "noscript", "iframe"];
                    tags.forEach(t => document.querySelectorAll(t).forEach(e => e.remove()));
                    return document.body?.innerText || "";
                }
            """)

            links = []
            if extract_links:
                links = await page.evaluate("""
                    () => [...document.querySelectorAll("a[href]")]
                        .slice(0, 50)
                        .map(a => ({text: a.innerText.trim(), href: a.href}))
                        .filter(a => a.text && a.href)
                """)

            return PageContent(
                url=url,
                title=title,
                text=text.strip(),
                links=links,
            )
