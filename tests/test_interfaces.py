from __future__ import annotations

from fastapi.testclient import TestClient

from interface.http_app import app
from interface import mcp_app


def test_health_endpoint():
	client = TestClient(app)
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


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
	assert "Tasks" in response.text
	assert "Reflection" in response.text


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


def test_mcp_tools_and_call_path(monkeypatch):
	monkeypatch.setattr(
		mcp_app,
		"_run_query",
		lambda query: {"final_report": f"report for {query}"},
	)

	tools = mcp_app.get_tools()
	assert tools and tools[0].name == "research_search"
	assert mcp_app.call_tool("research_search", "demo")["final_report"] == "report for demo"
