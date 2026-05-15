from __future__ import annotations

from agents.planner import plan_research
from agents.reflection import run_reflection
from agents.summarize import run_summarize


class FakeAdapter:
	def __init__(self, raw):
		self.raw = raw
		self.calls: list[tuple[list[object], str]] = []

	def complete(self, messages, *, system_prompt: str = "", temperature: float = 0.0):
		self.calls.append((list(messages), system_prompt))
		return type(
			"Response",
			(),
			{
				"provider": "test",
				"model": "test",
				"content": "{}",
				"raw": self.raw,
			},
		)()


def test_roles_use_model_adapter(monkeypatch):
	planner_adapter = FakeAdapter({"tasks": ["Task A"], "search_queries": ["Query A"]})
	summarize_adapter = FakeAdapter({"bullets": ["Bullet A"], "short_summary": "Bullet A"})
	reflection_adapter = FakeAdapter(
		{
			"gap": "1 item(s) need more evidence.",
			"next_action": "Refine search queries and re-run crawl.",
			"should_continue": True,
			"failed_urls": ["https://example.com/a"],
		}
	)

	monkeypatch.setattr("agents.planner.create_model_adapter", lambda provider, model_name: planner_adapter)
	monkeypatch.setattr("agents.summarize.create_model_adapter", lambda provider, model_name: summarize_adapter)
	monkeypatch.setattr("agents.reflection.create_model_adapter", lambda provider, model_name: reflection_adapter)

	state = plan_research({"user_query": "example topic"})
	state["documents"] = [
		{
			"url": "https://example.com/article",
			"title": "Example Article",
			"content": "First sentence. Second sentence. Third sentence.",
		}
	]
	state = run_summarize(state)
	state["verified_results"] = [
		{
			"url": "https://example.com/article",
			"status": "failed",
		}
	]
	state = run_reflection(state)

	assert state["tasks"] == ["Task A"]
	assert state["search_queries"] == ["Query A", "https://example.com/article"]
	assert state["summaries"][0]["bullets"] == ["Bullet A"]
	assert state["reflection"]["gap"] == "1 item(s) need more evidence."
	assert len(planner_adapter.calls) == 1
	assert len(summarize_adapter.calls) == 1
	assert len(reflection_adapter.calls) == 1