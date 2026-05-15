"""Orchestrator for the multi-agent research workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import settings
from models import ResearchState
from agents.planner import plan_research
from agents.search import run_search
from agents.crawl import run_crawl
from agents.summarize import run_summarize
from agents.verify import run_verify
from agents.reflection import run_reflection


def _ensure_state(state: ResearchState | None, user_query: str | None = None) -> ResearchState:
	base_state: ResearchState = {
		"user_query": user_query or "",
		"tasks": [],
		"search_queries": [],
		"search_results": [],
		"documents": [],
		"summaries": [],
		"verified_results": [],
		"reflection": {},
		"final_report": "",
		"citations": [],
	}
	if state:
		base_state.update(state)
	base_state.setdefault("_round", 0)
	return base_state


@dataclass(slots=True)
class Orchestrator:
	settings: Any = field(default_factory=lambda: settings)
	snapshots: list[ResearchState] = field(default_factory=list)

	def run(self, user_query: str, state: ResearchState | None = None) -> ResearchState:
		current = _ensure_state(state, user_query)
		max_rounds = max(1, int(getattr(self.settings, "max_rounds", 1)))

		current = plan_research(current)
		for round_number in range(1, max_rounds + 1):
			current["_round"] = round_number
			current = run_search(current)
			current = run_crawl(current)
			current = run_summarize(current)
			current = run_verify(current)
			current = run_reflection(current)
			self.snapshots.append(current.copy())
			reflection = current.get("reflection", {})
			should_continue = bool(reflection.get("should_continue"))
			if not should_continue:
				break
		current["final_report"] = self.build_final_report(current)
		return current

	def build_final_report(self, state: ResearchState) -> str:
		tasks = state.get("tasks", [])
		summaries = state.get("summaries", [])
		verified_results = state.get("verified_results", [])
		reflection = state.get("reflection", {})
		round_number = state.get("_round", 0)
		reflection_gap = reflection.get("gap", "") if isinstance(reflection, dict) else str(reflection)
		reflection_next_action = reflection.get("next_action", "") if isinstance(reflection, dict) else ""
		failed_urls = reflection.get("failed_urls", []) if isinstance(reflection, dict) else []
		failed_urls_text = ", ".join(failed_urls) if isinstance(failed_urls, list) and failed_urls else "None"
		lines = [
			"Research Report",
			"",
			f"Query: {state.get('user_query', '')}",
			f"Rounds: {round_number}",
			f"Tasks completed: {len(tasks)}",
			f"Summaries generated: {len(summaries)}",
			f"Verified results: {len(verified_results)}",
			"",
			"Reflection",
			f"- Gap: {reflection_gap or 'None'}",
			f"- Next action: {reflection_next_action or 'Finalize the report.'}",
			f"- Continue: {reflection.get('should_continue', False) if isinstance(reflection, dict) else False}",
			f"- Failed URLs: {failed_urls_text}",
		]
		return "\n".join(lines)
