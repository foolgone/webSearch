from __future__ import annotations

from orchestrator import Orchestrator
from agents import search as search_agent
from agents import crawl as crawl_agent


def test_orchestrator_runs_full_pipeline(monkeypatch):
    search_calls: list[str] = []

    monkeypatch.setattr(
        search_agent,
        "search_web",
        lambda query: search_calls.append(query) or [
            {
                "title": f"Result for {query}",
                "url": "https://example.com/article",
                "snippet": "Example snippet",
            }
        ],
    )
    monkeypatch.setattr(
        crawl_agent,
        "fetch_url",
        lambda url: "<html><head><title>Example Article</title></head><body><h1>Example Article</h1><p>This is sample content.</p></body></html>",
    )

    orchestrator = Orchestrator()
    result = orchestrator.run("example topic")

    assert result["user_query"] == "example topic"
    assert result["tasks"]
    assert result["search_queries"]
    assert len(search_calls) >= 1
    assert len(result["search_results"]) >= 1
    assert len(result["documents"]) >= 1
    assert len(result["summaries"]) >= 1
    assert len(result["verified_results"]) >= 1
    assert result["reflection"]
    assert "Rounds:" in result["final_report"]
    assert "Query: example topic" in result["final_report"]
