"""Fetch tool for retrieving HTML content."""

from __future__ import annotations

import httpx


DEFAULT_HEADERS = {
    "User-Agent": "webSearch/0.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_url(url: str, timeout: int = 20) -> str:
    response = httpx.get(
        url,
        headers=DEFAULT_HEADERS,
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text
