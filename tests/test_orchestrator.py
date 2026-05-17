from __future__ import annotations

from types import SimpleNamespace

import orchestrator as orchestrator_module
from orchestrator import Orchestrator
from agents import search as search_agent
from agents import crawl as crawl_agent
from services.state_store import InMemoryStateStore


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
	assert "Run ID:" in result["final_report"]
	assert "Stage timings" in result["final_report"]
	assert "1. 最终答案" in result["final_report"]
	assert "2. 分点总结" in result["final_report"]
	assert "3. Citation" in result["final_report"]
	assert "4. 来源链接" in result["final_report"]
	assert "5. 推理依据" in result["final_report"]
	assert "6. 输出质量控制" in result["final_report"]


def test_orchestrator_final_report_includes_preview_sections(monkeypatch):
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

	orchestrator = Orchestrator(settings=SimpleNamespace(max_rounds=1))
	result = orchestrator.run("example topic")

	assert "1. 最终答案" in result["final_report"]
	assert "2. 分点总结" in result["final_report"]
	assert "3. Citation" in result["final_report"]
	assert "4. 来源链接" in result["final_report"]
	assert "5. 推理依据" in result["final_report"]
	assert "6. 输出质量控制" in result["final_report"]
	assert "example.com/article" in result["final_report"]
	assert result["telemetry"]["run_id"]
	assert result["telemetry"]["stage_durations"]
	assert result["quality_control"]["checks"]["summary_links_covered"]


def test_orchestrator_can_resume_from_reflection_checkpoint(monkeypatch):
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

	store = InMemoryStateStore()
	orchestrator = Orchestrator(settings=SimpleNamespace(max_rounds=1), state_store=store)
	result = orchestrator.run("example topic")
	partial_state = dict(result)
	partial_state.pop("final_report", None)
	partial_state.pop("quality_control", None)
	partial_state["_workflow_stage"] = "Reflection"
	store.checkpoints[result["run_id"]] = [partial_state]

	resumed = orchestrator.resume(result["run_id"], user_query="example topic")
	assert resumed["_workflow_stage"] == "Complete"
	assert "Research Report" in resumed["final_report"]
	assert resumed["run_id"] == result["run_id"]
