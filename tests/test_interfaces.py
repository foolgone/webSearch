from __future__ import annotations

from fastapi.testclient import TestClient

from interface.http_app import app
from interface import mcp_app
from services.state_store import InMemoryStateStore


def test_health_endpoint():
	client = TestClient(app)
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_favicon_route_exists():
	client = TestClient(app)
	response = client.get("/favicon.ico")

	assert response.status_code == 204


def test_web_ui_renders_html(monkeypatch):
	client = TestClient(app)
	monkeypatch.setattr(
		"interface.http_app._run_query",
		lambda query: {
			"_round": 1,
			"tasks": ["Task 1"],
			"summaries": ["Summary 1"],
			"verified_results": ["Verified 1"],
			"reflection": {"gap": "None", "next_action": "Finalize", "should_continue": False, "failed_urls": []},
			"final_report": "Research Report\nQuery: demo",
		},
	)

	response = client.get("/search", params={"query": "demo"})

	assert response.status_code == 200
	assert "Research Report" in response.text
	assert "任务" in response.text
	assert "反思" in response.text
	assert "最终报告" in response.text


def test_json_api_returns_state(monkeypatch):
	client = TestClient(app)
	monkeypatch.setattr(
		"interface.http_app._run_query",
		lambda query: {
			"_round": 2,
			"tasks": ["Task 1"],
			"search_results": [{"url": "https://example.com"}],
			"documents": [{"url": "https://example.com"}],
			"summaries": [{"url": "https://example.com"}],
			"verified_results": [{"url": "https://example.com"}],
			"reflection": {"gap": "None", "next_action": "Finalize", "should_continue": False, "failed_urls": []},
			"final_report": "Research Report\nQuery: demo",
		},
	)

	response = client.get("/api/search", params={"query": "demo"})

	assert response.status_code == 200
	body = response.json()
	assert body["query"] == "demo"
	assert body["rounds"] == 2
	assert body["final_report"].startswith("Research Report")
	assert "run_id" in body


def test_run_lookup_and_resume_endpoints(monkeypatch):
	client = TestClient(app)
	store = InMemoryStateStore()
	run_id = "run-123"
	store.save_checkpoint(
		run_id,
		"Reflection",
		{
			"run_id": run_id,
			"user_query": "demo",
			"_round": 1,
			"_workflow_stage": "Reflection",
			"tasks": ["Task 1"],
			"search_queries": ["demo"],
			"search_results": [],
			"documents": [],
			"summaries": [],
			"verified_results": [],
			"reflection": {"gap": "None", "next_action": "Finalize", "should_continue": False, "failed_urls": []},
			"final_report": "Research Report\nQuery: demo",
			"citations": [],
			"telemetry": {},
		},
	)

	class StubOrchestrator:
		def __init__(self) -> None:
			self.state_store = store

		def run(self, user_query: str, state=None, resume_run_id: str | None = None):
			loaded = self.state_store.load_latest(resume_run_id or run_id)
			assert loaded is not None
			loaded = dict(loaded)
			loaded["final_report"] = "Research Report\nQuery: demo\nResumed"
			loaded["_workflow_stage"] = "Complete"
			return loaded

	monkeypatch.setattr("interface.http_app._get_orchestrator", lambda: StubOrchestrator())

	lookup = client.get(f"/api/runs/{run_id}")
	assert lookup.status_code == 200
	assert lookup.json()["run_id"] == run_id

	resumed = client.post(f"/api/runs/{run_id}/resume", params={"query": "demo"})
	assert resumed.status_code == 200
	assert resumed.json()["_workflow_stage"] == "Complete"
	assert "Resumed" in resumed.json()["final_report"]


def test_mcp_tools_and_call_path(monkeypatch):
	monkeypatch.setattr(
		mcp_app,
		"_run_query",
		lambda query: {"final_report": f"report for {query}"},
	)

	tools = mcp_app.get_tools()
	assert tools and tools[0].name == "research_search"
	assert mcp_app.call_tool("research_search", "demo")["final_report"] == "report for demo"
