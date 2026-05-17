"""Planner agent."""

from __future__ import annotations

from models import ResearchState
from config import settings
from services.model_adapter import ModelMessage, create_model_adapter
from services.retry import retry_operation


def plan_research(state: ResearchState) -> ResearchState:
	user_query = state.get("user_query", "").strip()
	adapter = create_model_adapter(settings.model_provider, settings.model_name)
	response = retry_operation(
		"planner-complete",
		lambda: adapter.complete(
			[ModelMessage(role="user", content=user_query)],
			system_prompt="Planner agent",
		),
		attempts=max(1, settings.retry_attempts),
		base_delay_seconds=settings.retry_backoff_seconds,
		backoff_multiplier=settings.retry_backoff_multiplier,
		stage="Planner",
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
