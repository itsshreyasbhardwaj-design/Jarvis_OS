"""
Web Search
==========
Keyless web search with a provider chain — no API key, no browser, no native
dependencies, just HTTPS GETs, so it runs anywhere:

  1. DuckDuckGo Instant Answer — great for entities/definitions.
  2. Wikipedia search — reliable general fallback for factual queries.

The first provider that returns results wins. The provider list is injectable
(``providers=[...]``) so parsing and chaining are fully testable without
network, and any network/parse failure degrades to an empty list rather than
raising.

Usage:
    web = WebSearch()
    results = await web.search("tallest mountain on Earth", max_results=3)
    for r in results:
        print(r.title, r.url)
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from html import unescape
from typing import Any

from loguru import logger

__all__ = ["SearchResult", "WebSearch"]

DDG_ENDPOINT = "https://api.duckduckgo.com/"
WIKIPEDIA_ENDPOINT = "https://en.wikipedia.org/w/api.php"
_USER_AGENT = "jarvis-os/0.1 (personal assistant)"
_TAG_RE = re.compile(r"<[^>]+>")

Provider = Callable[[str, int], Awaitable[list["SearchResult"]]]


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str
    source: str = "duckduckgo"


class WebSearch:
    """
    Keyless web search across a provider chain (DuckDuckGo → Wikipedia).

    Usage:
        web = WebSearch(timeout=8.0)
        results = await web.search("who wrote dune", max_results=5)
    """

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        providers: list[Provider] | None = None,
    ) -> None:
        self._timeout = timeout
        self._providers: list[Provider] = (
            list(providers)
            if providers is not None
            else [self._duckduckgo, self._wikipedia]
        )

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Return results from the first provider that yields any; else empty."""
        query = query.strip()
        if not query:
            return []
        for provider in self._providers:
            try:
                results = await provider(query, max_results)
            except Exception as exc:  # network, JSON, or missing httpx — try next
                name = getattr(provider, "__name__", repr(provider))
                logger.warning("Search provider {} failed for {!r}: {}", name, query, exc)
                continue
            if results:
                return results[:max_results]
        return []

    # --- Providers ---

    async def _duckduckgo(self, query: str, max_results: int) -> list[SearchResult]:
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "t": "jarvis-os",
        }
        data = await self._get_json(DDG_ENDPOINT, params)
        return self._parse_ddg(data, query, max_results)

    async def _wikipedia(self, query: str, max_results: int) -> list[SearchResult]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results,
        }
        data = await self._get_json(WIKIPEDIA_ENDPOINT, params)
        return self._parse_wikipedia(data, max_results)

    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(
            timeout=self._timeout, headers={"User-Agent": _USER_AGENT}
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return dict(response.json())

    # --- Parsers (pure, unit-testable) ---

    @staticmethod
    def _parse_ddg(data: dict[str, Any], query: str, max_results: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        abstract = (data.get("AbstractText") or "").strip()
        if abstract:
            results.append(
                SearchResult(
                    title=(data.get("Heading") or query).strip(),
                    url=data.get("AbstractURL") or "",
                    snippet=abstract,
                )
            )
        for topic in data.get("RelatedTopics", []):
            if len(results) >= max_results:
                break
            if topic.get("Text"):
                results.append(WebSearch._topic_to_result(topic))
            else:
                for sub in topic.get("Topics", []):
                    if len(results) >= max_results:
                        break
                    if sub.get("Text"):
                        results.append(WebSearch._topic_to_result(sub))
        return results[:max_results]

    @staticmethod
    def _parse_wikipedia(data: dict[str, Any], max_results: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        for hit in data.get("query", {}).get("search", []):
            title = hit.get("title", "")
            if not title:
                continue
            results.append(
                SearchResult(
                    title=title,
                    url="https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
                    snippet=_strip_html(hit.get("snippet", "")),
                    source="wikipedia",
                )
            )
            if len(results) >= max_results:
                break
        return results

    @staticmethod
    def _topic_to_result(topic: dict[str, Any]) -> SearchResult:
        text = topic.get("Text", "")
        return SearchResult(
            title=text.split(" - ")[0][:80],
            url=topic.get("FirstURL", ""),
            snippet=text,
        )


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities (Wikipedia snippets contain both)."""
    return unescape(_TAG_RE.sub("", text)).strip()
