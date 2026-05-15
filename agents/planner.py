"""Planner agent."""

from __future__ import annotations

from models import ResearchState
from config import settings
from services.model_adapter import ModelMessage, create_model_adapter


def plan_research(state: ResearchState) -> ResearchState:
	user_query = state.get("user_query", "").strip()
	adapter = create_model_adapter(settings.model_provider, settings.model_name)
	response = adapter.complete(
		[ModelMessage(role="user", content=user_query)],
		system_prompt="Planner agent",
	)
	payload = response.raw if isinstance(response.raw, dict) else {}
	if payload.get("tasks"):
		state["tasks"] = list(payload["tasks"])
	else:
		state["tasks"] = [
			f"Understand the research question: {user_query}",
			"Find relevant sources",
			"Summarize the sources",
			"Verify the evidence",
		]
	state["search_queries"] = list(payload.get("search_queries", [user_query] if user_query else []))
	return state
