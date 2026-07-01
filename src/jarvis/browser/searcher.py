"""
Web Searcher
============
Performs web searches and extracts clean results.
Supports Google, DuckDuckGo, and Bing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from jarvis.browser.browser_manager import BrowserManager


@dataclass
class SearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str
    position: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class WebSearcher:
    """
    Performs web searches via browser automation.

    Usage:
        searcher = WebSearcher(browser_manager)
        results = await searcher.search("Python asyncio tutorial", limit=5)
        for r in results:
            print(r.title, r.url)
    """

    SEARCH_ENGINES = {
        "duckduckgo": "https://duckduckgo.com/?q={query}&kp=-1&kl=us-en",
        "google": "https://www.google.com/search?q={query}",
        "bing": "https://www.bing.com/search?q={query}",
    }

    def __init__(
        self,
        browser_manager: BrowserManager,
        default_engine: str = "duckduckgo",
    ) -> None:
        self._browser = browser_manager
        self._engine = default_engine

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        engine: str | None = None,
    ) -> list[SearchResult]:
        """Perform a web search and return structured results."""
        engine = engine or self._engine
        url_template = self.SEARCH_ENGINES.get(engine)
        if not url_template:
            raise ValueError(f"Unknown search engine: {engine}")

        import urllib.parse
        url = url_template.format(query=urllib.parse.quote(query))
        logger.info(f"Searching: {query!r} via {engine}")

        async with self._browser.new_page() as page:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            results = await self._extract_results(page, engine, limit)

        logger.debug(f"Search returned {len(results)} results")
        return results

    async def fetch_page_content(self, url: str) -> str:
        """Fetch and extract clean text content from a URL."""
        async with self._browser.new_page() as page:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")

            # Extract main content
            content = await page.evaluate("""
                () => {
                    const selectors = ['article', 'main', '[role=main]', '.content', '#content'];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) return el.innerText;
                    }
                    return document.body.innerText;
                }
            """)
        return str(content)

    async def _extract_results(
        self, page: Any, engine: str, limit: int
    ) -> list[SearchResult]:
        """Extract search results from page DOM."""
        results: list[SearchResult] = []

        if engine == "duckduckgo":
            items = await page.query_selector_all("[data-result='web']")
            for i, item in enumerate(items[:limit]):
                try:
                    title_el = await item.query_selector("a[data-testid='result-title-a']")
                    snippet_el = await item.query_selector("[data-result='snippet']")
                    if not title_el:
                        continue
                    title = await title_el.inner_text()
                    url = await title_el.get_attribute("href") or ""
                    snippet = await snippet_el.inner_text() if snippet_el else ""
                    results.append(SearchResult(
                        title=title.strip(),
                        url=url,
                        snippet=snippet.strip(),
                        position=i + 1,
                    ))
                except Exception:
                    continue

        return results
