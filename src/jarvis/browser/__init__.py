"""Browser automation layer via Playwright."""

from jarvis.browser.browser_manager import BrowserManager
from jarvis.browser.extractor import ContentExtractor, PageContent
from jarvis.browser.searcher import SearchResult, WebSearcher

__all__ = [
    "BrowserManager",
    "WebSearcher",
    "SearchResult",
    "ContentExtractor",
    "PageContent",
]
