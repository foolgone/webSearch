"""Reflection agent."""

from __future__ import annotations

from models import ResearchState


def run_reflection(state: ResearchState) -> ResearchState:
	verified_results = state.get("verified_results", [])
	failed_items = [item for item in verified_results if item.get("status") != "passed"]

	if failed_items:
		state["reflection"] = {
			"gap": f"{len(failed_items)} item(s) need more evidence.",
			"next_action": "Refine search queries and re-run crawl.",
			"should_continue": True,
			"failed_urls": [item.get("url", "") for item in failed_items],
		}
		additional_queries = state.get("search_queries", [])
		for item in failed_items:
			url = str(item.get("url", "")).strip()
			if url and url not in additional_queries:
				additional_queries.append(url)
		state["search_queries"] = additional_queries
	else:
		state["reflection"] = {
			"gap": "No major evidence gaps detected.",
			"next_action": "Finalize the report.",
			"should_continue": False,
			"failed_urls": [],
		}
	return state
