"""Search tool that queries DuckDuckGo HTML search results."""

from __future__ import annotations

from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup


DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


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

    try:
        response = httpx.get(
            DDG_SEARCH_URL,
            params={"q": normalized_query},
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
            return results
    except httpx.RequestError as exc:
        return [
            {
                "title": normalized_query,
                "url": f"https://duckduckgo.com/?q={quote_plus(normalized_query)}",
                "snippet": f"Search fallback used because network search failed: {exc}",
            }
        ]

    search_url = f"https://duckduckgo.com/?q={quote_plus(normalized_query)}"
    return [
        {
            "title": normalized_query,
            "url": search_url,
            "snippet": "No HTML search results parsed; using DuckDuckGo search page.",
        }
    ]
