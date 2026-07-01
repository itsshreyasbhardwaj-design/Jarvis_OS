"""Unit tests for keyless web search: provider-chain logic + parsers."""

from __future__ import annotations

import pytest

from jarvis.integrations.web_search import SearchResult, WebSearch

DDG_SAMPLE = {
    "Heading": "Python (programming language)",
    "AbstractText": "Python is a high-level, general-purpose programming language.",
    "AbstractURL": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "RelatedTopics": [
        {"Text": "Guido van Rossum - creator", "FirstURL": "https://example.com/guido"},
        {"Topics": [{"Text": "PyPI - the Python Package Index", "FirstURL": "https://pypi.org"}]},
    ],
}

WIKI_SAMPLE = {
    "query": {
        "search": [
            {"title": "Tallest mountain", "snippet": "the <b>tall</b> &amp; high peak"},
            {"title": "List of highest mountains on Earth", "snippet": "Earth's peaks."},
        ]
    }
}


@pytest.mark.unit
class TestProviderChain:
    @pytest.mark.asyncio
    async def test_first_provider_with_results_wins(self) -> None:
        async def first(_q: str, _n: int) -> list[SearchResult]:
            return [SearchResult(title="A", url="", snippet="")]

        async def second(_q: str, _n: int) -> list[SearchResult]:
            raise AssertionError("second provider must not be reached")

        web = WebSearch(providers=[first, second])
        results = await web.search("x")
        assert results[0].title == "A"

    @pytest.mark.asyncio
    async def test_falls_through_empty_provider(self) -> None:
        async def empty(_q: str, _n: int) -> list[SearchResult]:
            return []

        async def good(_q: str, _n: int) -> list[SearchResult]:
            return [SearchResult(title="B", url="", snippet="")]

        web = WebSearch(providers=[empty, good])
        assert (await web.search("x"))[0].title == "B"

    @pytest.mark.asyncio
    async def test_provider_error_is_skipped(self) -> None:
        async def boom(_q: str, _n: int) -> list[SearchResult]:
            raise RuntimeError("network down")

        async def good(_q: str, _n: int) -> list[SearchResult]:
            return [SearchResult(title="C", url="", snippet="")]

        web = WebSearch(providers=[boom, good])
        assert (await web.search("x"))[0].title == "C"

    @pytest.mark.asyncio
    async def test_empty_query_short_circuits(self) -> None:
        async def unused(_q: str, _n: int) -> list[SearchResult]:
            raise AssertionError("must not run for empty query")

        web = WebSearch(providers=[unused])
        assert await web.search("   ") == []

    @pytest.mark.asyncio
    async def test_all_empty_returns_empty(self) -> None:
        async def empty(_q: str, _n: int) -> list[SearchResult]:
            return []

        web = WebSearch(providers=[empty])
        assert await web.search("x") == []

    @pytest.mark.asyncio
    async def test_max_results_respected(self) -> None:
        async def many(_q: str, _n: int) -> list[SearchResult]:
            return [SearchResult(title=str(i), url="", snippet="") for i in range(10)]

        web = WebSearch(providers=[many])
        assert len(await web.search("x", max_results=2)) == 2


@pytest.mark.unit
class TestParsers:
    def test_parse_ddg_abstract_and_nested_topics(self) -> None:
        results = WebSearch._parse_ddg(DDG_SAMPLE, "python", 5)
        assert results[0].title == "Python (programming language)"
        assert "high-level" in results[0].snippet
        assert any("pypi.org" in r.url for r in results)  # nested topic flattened

    def test_parse_wikipedia_strips_html_and_builds_url(self) -> None:
        results = WebSearch._parse_wikipedia(WIKI_SAMPLE, 5)
        assert results[0].title == "Tallest mountain"
        assert results[0].url.endswith("/wiki/Tallest_mountain")
        assert results[0].source == "wikipedia"
        assert "<" not in results[0].snippet  # tags stripped
        assert "&amp;" not in results[0].snippet  # entities unescaped
        assert "& high" in results[0].snippet  # &amp; -> &
