"""Fetch tool for retrieving HTML content."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

import httpx

from config import settings


DEFAULT_HEADERS = {
    "User-Agent": "webSearch/0.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(slots=True)
class FetchResult:
    url: str
    html: str
    mode: str


DynamicFetcher = Callable[[str, int], str]


def _fetch_dynamic_html_playwright(url: str, timeout: int = 20) -> str:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - optional dependency path
        raise NotImplementedError(
            "Dynamic fetch requires Playwright. Install the optional dependency to enable it."
        ) from exc

    async def _render() -> str:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page(extra_http_headers=DEFAULT_HEADERS)
                await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
                return await page.content()
            finally:
                await browser.close()

    return asyncio.run(_render())


_dynamic_fetcher: DynamicFetcher = _fetch_dynamic_html_playwright


def set_dynamic_fetcher(fetcher: DynamicFetcher) -> None:
    global _dynamic_fetcher
    _dynamic_fetcher = fetcher


def _looks_dynamic(url: str) -> bool:
    lower_url = url.lower()
    return any(
        token in lower_url
        for token in (
            "/login",
            "/signin",
            "/signup",
            "/register",
            "/app",
            "/dashboard",
            "/search",
            "?",
        )
    )


def _host_matches_dynamic_domain(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in (settings.dynamic_fetch_domains or []))


def _html_looks_dynamic(html: str) -> bool:
    lowered_html = html.lower()
    markers = (
        "__next",
        "__nuxt",
        "data-reactroot",
        "window.__initial_state__",
        "window.__next_data__",
        "enable javascript",
        "turn on javascript",
        "please enable javascript",
        "loading...",
    )
    return any(marker in lowered_html for marker in markers)


def fetch_url(url: str, timeout: int = 20) -> str:
    response = httpx.get(
        url,
        headers=DEFAULT_HEADERS,
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def fetch_dynamic_url(url: str, timeout: int = 20) -> str:
    return _dynamic_fetcher(url, timeout)


def fetch_html(url: str, timeout: int = 20, mode: str = "auto") -> FetchResult:
    selected_mode = mode.strip().lower()
    if selected_mode == "dynamic" or (selected_mode == "auto" and _host_matches_dynamic_domain(url)):
        html = fetch_dynamic_url(url, timeout=timeout)
        return FetchResult(url=url, html=html, mode="dynamic")

    html = fetch_url(url, timeout=timeout)
    if selected_mode == "auto" and _html_looks_dynamic(html):
        dynamic_html = fetch_dynamic_url(url, timeout=timeout)
        return FetchResult(url=url, html=dynamic_html, mode="dynamic")

    return FetchResult(url=url, html=html, mode="static")
