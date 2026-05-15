"""Planner agent."""

from __future__ import annotations

from models import ResearchState


def plan_research(state: ResearchState) -> ResearchState:
	user_query = state.get("user_query", "").strip()
	state["tasks"] = [
		f"Understand the research question: {user_query}",
		"Find relevant sources",
		"Summarize the sources",
		"Verify the evidence",
	]
	state["search_queries"] = [user_query] if user_query else []
	return state
