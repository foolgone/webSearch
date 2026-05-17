from __future__ import annotations

import httpx

from agents.crawl import run_crawl
from tools.cache import clear_cache
import tools.fetch as fetch_module
from tools.fetch import fetch_html, fetch_dynamic_url, set_dynamic_fetcher
from tools import search as search_tool


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_search_web_caches_successful_queries(monkeypatch):
    clear_cache()
    calls: list[str] = []

    html = """
    <html>
      <body>
        <div class="result">
          <a class="result__a" href="https://example.com/a">Example A</a>
          <a class="result__snippet">Snippet A</a>
        </div>
      </body>
    </html>
    """

    def fake_get(url, params=None, headers=None, timeout=None, follow_redirects=None):
        calls.append(params["q"])
        return FakeResponse(html)

    monkeypatch.setattr(search_tool.httpx, "get", fake_get)

    first = search_tool.search_web("  example topic  ")
    second = search_tool.search_web("example topic")

    assert first == second
    assert len(calls) == 1
    assert first[0]["title"] == "Example A"


def test_search_web_caches_network_fallback(monkeypatch):
    clear_cache()
    calls: list[str] = []

    def fake_get(url, params=None, headers=None, timeout=None, follow_redirects=None):
        calls.append(params["q"])
        request = httpx.Request("GET", url)
        raise httpx.ConnectError("boom", request=request)

    monkeypatch.setattr(search_tool.httpx, "get", fake_get)

    first = search_tool.search_web("network issue")
    second = search_tool.search_web("network issue")

    assert first == second
    assert len(calls) == 3
    assert "Search fallback used because network search failed" in first[0]["snippet"]


def test_search_web_recovers_after_transient_failure(monkeypatch):
    clear_cache()
    calls: list[str] = []

    html = """
    <html>
      <body>
        <div class="result">
          <a class="result__a" href="https://example.com/a">Example A</a>
          <a class="result__snippet">Snippet A</a>
        </div>
      </body>
    </html>
    """

    def fake_get(url, params=None, headers=None, timeout=None, follow_redirects=None):
        calls.append(params["q"])
        if len(calls) < 2:
            request = httpx.Request("GET", url)
            raise httpx.ConnectError("boom", request=request)
        return FakeResponse(html)

    monkeypatch.setattr(search_tool.httpx, "get", fake_get)

    results = search_tool.search_web("transient issue")

    assert len(calls) == 2
    assert results[0]["url"] == "https://example.com/a"


def test_search_web_skips_cache_for_direct_urls(monkeypatch):
    clear_cache()
    cache_hits: list[str] = []
    cache_sets: list[tuple[str, object, int]] = []

    monkeypatch.setattr(search_tool, "get_cached", lambda key: cache_hits.append(key) or None)
    monkeypatch.setattr(
        search_tool,
        "set_cached",
        lambda key, value, ttl_seconds=300: cache_sets.append((key, value, ttl_seconds)),
    )

    result = search_tool.search_web("https://example.com/article")

    assert result == [
        {
            "title": "https://example.com/article",
            "url": "https://example.com/article",
            "snippet": "Direct URL query.",
        }
    ]
    assert cache_hits == []
    assert cache_sets == []


def test_search_web_uses_injected_provider(monkeypatch):
    clear_cache()
    calls: list[str] = []

    class FakeProvider:
        def search(self, query: str):
            calls.append(query)
            return search_tool.SearchBatch(
                results=[
                    {
                        "title": f"Injected {query}",
                        "url": "https://example.com/injected",
                        "snippet": "Injected result",
                    }
                ],
                ttl_seconds=3600,
            )

    monkeypatch.setattr(search_tool, "_search_provider", FakeProvider())

    first = search_tool.search_web("provider topic")
    second = search_tool.search_web("provider topic")

    assert first == second
    assert len(calls) == 1
    assert first[0]["title"] == "Injected provider topic"


def test_search_web_decodes_duckduckgo_redirect_urls(monkeypatch):
        clear_cache()

        html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Farticle&amp;rut=abc">Example</a>
                    <a class="result__snippet">Snippet</a>
                </div>
            </body>
        </html>
        """

        monkeypatch.setattr(
                search_tool.httpx,
                "get",
                lambda url, params=None, headers=None, timeout=None, follow_redirects=None: FakeResponse(html),
        )

        results = search_tool.search_web("example topic")

        assert results[0]["url"] == "https://example.com/article"


def test_search_web_filters_duckduckgo_internal_links(monkeypatch):
        clear_cache()

        html = """
        <html>
            <body>
                <div class="result">
                    <a class="result__a" href="//duckduckgo.com/about">About DuckDuckGo</a>
                    <a class="result__snippet">Snippet</a>
                </div>
                <div class="result">
                    <a class="result__a" href="https://example.com/keep">Keep Me</a>
                    <a class="result__snippet">Snippet</a>
                </div>
            </body>
        </html>
        """

        monkeypatch.setattr(
                search_tool.httpx,
                "get",
                lambda url, params=None, headers=None, timeout=None, follow_redirects=None: FakeResponse(html),
        )

        results = search_tool.search_web("example topic")

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/keep"


def test_fetch_html_routes_to_static_by_default(monkeypatch):
    monkeypatch.setattr("tools.fetch.fetch_url", lambda url, timeout=20: "<html><title>Static</title><body>Static page</body></html>")
    monkeypatch.setattr("tools.fetch.fetch_dynamic_url", lambda url, timeout=20: (_ for _ in ()).throw(AssertionError("dynamic fetch should not be used")))

    result = fetch_html("https://example.com/article")

    assert result.mode == "static"
    assert "Static page" in result.html


def test_fetch_html_routes_to_dynamic_when_forced(monkeypatch):
    monkeypatch.setattr("tools.fetch.fetch_url", lambda url, timeout=20: (_ for _ in ()).throw(AssertionError("static fetch should not be used")))
    monkeypatch.setattr("tools.fetch.fetch_dynamic_url", lambda url, timeout=20: "<html><title>Dynamic</title><body>Dynamic page</body></html>")

    result = fetch_html("https://example.com/dashboard", mode="dynamic")

    assert result.mode == "dynamic"
    assert "Dynamic page" in result.html


def test_fetch_url_recovers_after_transient_failure(monkeypatch):
    calls: list[str] = []

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        calls.append(url)
        if len(calls) < 2:
            request = httpx.Request("GET", url)
            raise httpx.ConnectError("boom", request=request)
        return FakeResponse("<html><body>Recovered</body></html>")

    monkeypatch.setattr(fetch_module.httpx, "get", fake_get)

    html = fetch_module.fetch_url("https://example.com/article")

    assert len(calls) == 2
    assert "Recovered" in html


def test_fetch_html_routes_to_dynamic_for_configured_domains(monkeypatch):
    monkeypatch.setattr(fetch_module.settings, "dynamic_fetch_domains", ["example.com"])
    monkeypatch.setattr("tools.fetch.fetch_url", lambda url, timeout=20: (_ for _ in ()).throw(AssertionError("static fetch should not be used")))
    monkeypatch.setattr("tools.fetch.fetch_dynamic_url", lambda url, timeout=20: "<html><body>Config driven</body></html>")

    result = fetch_html("https://sub.example.com/article")

    assert result.mode == "dynamic"
    assert "Config driven" in result.html


def test_fetch_html_switches_to_dynamic_on_page_features(monkeypatch):
    monkeypatch.setattr(fetch_module.settings, "dynamic_fetch_domains", [])
    monkeypatch.setattr("tools.fetch.fetch_url", lambda url, timeout=20: "<html><head><script>window.__NEXT_DATA__ = {};</script></head><body>Loading...</body></html>")
    monkeypatch.setattr("tools.fetch.fetch_dynamic_url", lambda url, timeout=20: "<html><body>Rendered from features</body></html>")

    result = fetch_html("https://example.com/article")

    assert result.mode == "dynamic"
    assert "Rendered from features" in result.html


def test_dynamic_fetcher_can_be_injected(monkeypatch):
    captured: list[tuple[str, int]] = []
    original_fetcher = fetch_module._dynamic_fetcher

    set_dynamic_fetcher(lambda url, timeout=20: captured.append((url, timeout)) or "<html><body>Rendered</body></html>")

    try:
        result = fetch_dynamic_url("https://example.com/dashboard", timeout=12)
    finally:
        set_dynamic_fetcher(original_fetcher)

    assert result == "<html><body>Rendered</body></html>"
    assert captured == [("https://example.com/dashboard", 12)]


def test_run_crawl_marks_fetch_mode_source(monkeypatch):
    monkeypatch.setattr("agents.crawl.fetch_html", lambda url, mode="auto": type("FetchResult", (), {"html": "<html><head><title>Page</title></head><body><p>Body text.</p></body></html>", "mode": "dynamic"})())

    state = run_crawl(
        {
            "search_results": [
                {
                    "url": "https://example.com/dashboard",
                    "title": "Dashboard",
                    "snippet": "Snippet",
                    "fetch_mode": "dynamic",
                }
            ]
        }
    )

    assert state["documents"][0]["source"] == "dynamic"
    assert state["documents"][0]["title"] == "Page"