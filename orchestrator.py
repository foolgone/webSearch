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


def _format_summary_preview(summaries: list[dict[str, Any]], limit: int = 3) -> list[str]:
	lines: list[str] = []
	for index, summary in enumerate(summaries[:limit], start=1):
		url = str(summary.get("url", ""))
		bullets = summary.get("bullets", [])
		if not isinstance(bullets, list):
			bullets = []
		bullet_text = "；".join(str(bullet) for bullet in bullets[:3] if str(bullet).strip()) or "无可展示摘要"
		lines.append(f"{index}. {url}\n   - {bullet_text}")
	return lines


def _format_verified_preview(verified_results: list[dict[str, Any]], limit: int = 5) -> list[str]:
	lines: list[str] = []
	for index, item in enumerate(verified_results[:limit], start=1):
		url = str(item.get("url", ""))
		status = str(item.get("status", ""))
		notes = str(item.get("notes", ""))
		lines.append(f"{index}. [{status}] {url} - {notes}")
	return lines


def _build_final_answer(summaries: list[dict[str, Any]], verified_results: list[dict[str, Any]]) -> list[str]:
	passed_urls = {
		str(item.get("url", ""))
		for item in verified_results
		if str(item.get("status", "")).lower() in {"passed", "partial"}
	}
	answer_lines: list[str] = []
	for summary in summaries:
		url = str(summary.get("url", ""))
		if passed_urls and url not in passed_urls:
			continue
		bullets = summary.get("bullets", [])
		if not isinstance(bullets, list):
			bullets = []
		bullet_text = "；".join(str(bullet) for bullet in bullets[:2] if str(bullet).strip())
		if bullet_text:
			answer_lines.append(f"- {bullet_text}")
		if len(answer_lines) >= 3:
			break

	if answer_lines:
		return ["基于当前已核验资料，结论可概括为："] + answer_lines
	return ["当前证据不足，暂时只能确认已有资料还不足以收束为稳定结论，需要继续补充检索与核验。"]


def _build_bullet_summary(summaries: list[dict[str, Any]]) -> list[str]:
	lines: list[str] = []
	for index, summary in enumerate(summaries[:5], start=1):
		url = str(summary.get("url", ""))
		bullets = summary.get("bullets", [])
		if not isinstance(bullets, list):
			bullets = []
		bullet_text = "；".join(str(bullet) for bullet in bullets[:3] if str(bullet).strip()) or "无可展示摘要"
		lines.append(f"{index}. {bullet_text}（{url}）")
	return lines


def _build_citations(citations: list[dict[str, Any]], limit: int = 8) -> list[str]:
	lines: list[str] = []
	for index, item in enumerate(citations[:limit], start=1):
		url = str(item.get("url", ""))
		note = str(item.get("note", ""))
		location = str(item.get("location", ""))
		lines.append(f"{index}. {note} [{location}] {url}")
	return lines


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
		citations = state.get("citations", [])
		reflection = state.get("reflection", {})
		round_number = state.get("_round", 0)
		reflection_gap = reflection.get("gap", "") if isinstance(reflection, dict) else str(reflection)
		reflection_next_action = reflection.get("next_action", "") if isinstance(reflection, dict) else ""
		failed_urls = reflection.get("failed_urls", []) if isinstance(reflection, dict) else []
		failed_urls_text = ", ".join(failed_urls) if isinstance(failed_urls, list) and failed_urls else "None"
		final_answer = _build_final_answer(summaries, verified_results)
		bullet_summary = _build_bullet_summary(summaries)
		citation_lines = _build_citations(citations)
		source_links = []
		seen_urls: set[str] = set()
		for item in citations:
			url = str(item.get("url", "")).strip()
			if not url or url in seen_urls:
				continue
			seen_urls.add(url)
			source_links.append(url)
		lines = [
			"Research Report",
			"",
			f"Query: {state.get('user_query', '')}",
			f"Rounds: {round_number}",
			f"Tasks completed: {len(tasks)}",
			f"Summaries generated: {len(summaries)}",
			f"Verified results: {len(verified_results)}",
			"",
			"1. 最终答案",
			*final_answer,
			"",
			"2. 分点总结",
			*(bullet_summary or ["1. 无可展示摘要"]),
			"",
			"3. Citation",
			*(citation_lines or ["1. 暂无 citation"]),
			"",
			"4. 来源链接",
			*(source_links or ["暂无来源链接"]),
			"",
			"5. 推理依据",
			f"- 已核验结果数量: {len(verified_results)}",
			f"- 当前缺口: {reflection_gap or 'None'}",
			f"- 下一步: {reflection_next_action or 'Finalize the report.'}",
			f"- 是否继续: {reflection.get('should_continue', False) if isinstance(reflection, dict) else False}",
			f"- 失败链接: {failed_urls_text}",
		]
		return "\n".join(lines)
