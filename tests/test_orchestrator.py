from __future__ import annotations

from types import SimpleNamespace

import orchestrator as orchestrator_module
from orchestrator import Orchestrator
from agents import search as search_agent
from agents import crawl as crawl_agent


def test_orchestrator_stops_at_max_rounds(monkeypatch):
	monkeypatch.setattr(
		search_agent,
		"search_web",
		lambda query: [
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

	def always_continue(state):
		state["reflection"] = {
			"gap": "Force another round.",
			"next_action": "Continue.",
			"should_continue": True,
			"failed_urls": [],
		}
		return state

	monkeypatch.setattr(orchestrator_module, "run_reflection", always_continue)

	orchestrator = Orchestrator(settings=SimpleNamespace(max_rounds=2))
	result = orchestrator.run("example topic")

	assert result["_round"] == 2
	assert len(orchestrator.snapshots) == 2
	assert result["reflection"]["should_continue"] is True
	assert "Rounds: 2" in result["final_report"]
