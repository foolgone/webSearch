"""Reflection agent."""

from __future__ import annotations

from models import ResearchState
from config import settings
from services.model_adapter import ModelMessage, create_model_adapter
from services.retry import retry_operation


def run_reflection(state: ResearchState) -> ResearchState:
	verified_results = state.get("verified_results", [])
	failed_items = [item for item in verified_results if item.get("status") != "passed"]
	adapter = create_model_adapter(settings.model_provider, settings.model_name)
	response = retry_operation(
		"reflection-complete",
		lambda: adapter.complete(
			[
				ModelMessage(
					role="user",
					content="\n".join(
						[
							f"TOTAL_FAILED: {len(failed_items)}",
							f"FAILED_URLS: {' | '.join(str(item.get('url', '')).strip() for item in failed_items)}",
						],
					),
				),
			],
			system_prompt="Reflection agent",
		),
		attempts=max(1, settings.retry_attempts),
		base_delay_seconds=settings.retry_backoff_seconds,
		backoff_multiplier=settings.retry_backoff_multiplier,
		stage="Reflection",
	)
	payload = response.raw if isinstance(response.raw, dict) else {}

	if failed_items:
		state["reflection"] = {
			"gap": payload.get("gap", f"{len(failed_items)} item(s) need more evidence."),
			"next_action": payload.get("next_action", "Refine search queries and re-run crawl."),
			"should_continue": bool(payload.get("should_continue", True)),
			"failed_urls": payload.get("failed_urls", [item.get("url", "") for item in failed_items]),
		}
		additional_queries = state.get("search_queries", [])
		for item in failed_items:
			url = str(item.get("url", "")).strip()
			if url and url not in additional_queries:
				additional_queries.append(url)
		state["search_queries"] = additional_queries
	else:
		state["reflection"] = {
			"gap": payload.get("gap", "No major evidence gaps detected."),
			"next_action": payload.get("next_action", "Finalize the report."),
			"should_continue": bool(payload.get("should_continue", False)),
			"failed_urls": payload.get("failed_urls", []),
		}
	return state
