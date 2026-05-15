"""Search tool that queries DuckDuckGo HTML search results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from tools.cache import get_cached, set_cached


DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"


class SearchProvider(Protocol):
    def search(self, query: str) -> "SearchBatch":
        ...


@dataclass(slots=True)
class SearchBatch:
    results: list[dict[str, str]]
    ttl_seconds: int = 3600


def _get_search_cache_key(query: str) -> str:
    return f"search_web:{query}"


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


class DuckDuckGoHTMLSearchProvider:
    def search(self, query: str) -> SearchBatch:
        try:
            response = httpx.get(
                DDG_SEARCH_URL,
                params={"q": query},
                headers={"User-Agent": "webSearch/0.1"},
                timeout=20,
                follow_redirects=True,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results: list[dict[str, str]] = []
            seen: set[str] = set()

            for card in soup.select("div.result"):
                link = card.select_one("a.result__a")
                if not link:
                    continue
                url = link.get("href", "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                snippet_node = card.select_one("a.result__snippet, div.result__snippet")
                results.append(
                    {
                        "title": link.get_text(" ", strip=True),
                        "url": url,
                        "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
                    }
                )
                if len(results) >= 5:
                    break

            if results:
                return SearchBatch(results=results, ttl_seconds=3600)
        except httpx.RequestError as exc:
            return SearchBatch(
                results=[
                    {
                        "title": query,
                        "url": f"https://duckduckgo.com/?q={quote_plus(query)}",
                        "snippet": f"Search fallback used because network search failed: {exc}",
                    }
                ],
                ttl_seconds=300,
            )

        search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        return SearchBatch(
            results=[
                {
                    "title": query,
                    "url": search_url,
                    "snippet": "No HTML search results parsed; using DuckDuckGo search page.",
                }
            ],
            ttl_seconds=300,
        )


_search_provider: SearchProvider = DuckDuckGoHTMLSearchProvider()


def set_search_provider(provider: SearchProvider) -> None:
    global _search_provider
    _search_provider = provider


def search_web(query: str) -> list[dict[str, str]]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    if _looks_like_url(normalized_query):
        return [
            {
                "title": normalized_query,
                "url": normalized_query,
                "snippet": "Direct URL query.",
            }
        ]

    cache_key = _get_search_cache_key(normalized_query)
    cached_results = get_cached(cache_key)
    if cached_results is not None:
        return cached_results

    batch = _search_provider.search(normalized_query)
    if batch.results:
        set_cached(cache_key, batch.results, ttl_seconds=batch.ttl_seconds)
    return batch.results
