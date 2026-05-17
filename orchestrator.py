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
from services.observability import RunTelemetry
from services.state_store import StateStore, build_state_store
from services.quality import evaluate_output_quality


def _ensure_state(state: ResearchState | None, user_query: str | None = None) -> ResearchState:
	base_state: ResearchState = {
		"user_query": user_query or "",
		"run_id": "",
		"tasks": [],
		"search_queries": [],
		"search_results": [],
		"documents": [],
		"summaries": [],
		"verified_results": [],
		"reflection": {},
		"final_report": "",
		"citations": [],
		"telemetry": {},
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
	telemetry: RunTelemetry | None = None
	state_store: StateStore = field(default_factory=lambda: build_state_store(dsn=settings.postgres_dsn, schema=settings.postgres_schema))

	def _save_checkpoint(self, stage: str, state: ResearchState, *, is_final: bool = False) -> None:
		if not self.state_store:
			return
		self.state_store.save_checkpoint(str(state.get("run_id", "")), stage, state, is_final=is_final)

	@staticmethod
	def _next_stage(stage: str) -> str | None:
		stage_order = ["Planner", "Search", "Crawl", "Summarize", "Verify", "Reflection"]
		try:
			index = stage_order.index(stage)
		except ValueError:
			return None
		if index + 1 >= len(stage_order):
			return None
		return stage_order[index + 1]

	def _load_resume_state(self, run_id: str) -> ResearchState | None:
		if not self.state_store:
			return None
		return self.state_store.load_latest(run_id)

	def run(self, user_query: str, state: ResearchState | None = None, resume_run_id: str | None = None) -> ResearchState:
		current = state or None
		if current is None and resume_run_id:
			current = self._load_resume_state(resume_run_id)
		current = _ensure_state(current, user_query)
		telemetry = RunTelemetry()
		self.telemetry = telemetry
		current["run_id"] = current.get("run_id") or telemetry.run_id
		telemetry.emit("run_started", stage="core", message="run started", user_query=user_query)
		max_rounds = max(1, int(getattr(self.settings, "max_rounds", 1)))
		resume_stage = str(current.get("_workflow_stage", ""))
		if resume_stage == "Complete":
			return current
		if resume_stage == "Started":
			resume_stage = ""
		next_stage = self._next_stage(resume_stage) if resume_stage else None
		if not resume_stage:
			current["_workflow_stage"] = "Started"
			self._save_checkpoint("Started", current)

		if not resume_stage:
			telemetry.start_stage("Planner")
			current = plan_research(current)
			current["_workflow_stage"] = "Planner"
			self._save_checkpoint("Planner", current)
			telemetry.end_stage("Planner", tasks=len(current.get("tasks", [])), search_queries=len(current.get("search_queries", [])))
			next_stage = "Search"
		elif resume_stage == "Reflection":
			reflection = current.get("reflection", {})
			should_continue = bool(reflection.get("should_continue")) if isinstance(reflection, dict) else False
			round_number = int(current.get("_round", 0)) + 1 if should_continue and int(current.get("_round", 0)) < max_rounds else max_rounds + 1
			next_stage = "Search" if should_continue else None

		round_number = max(1, int(current.get("_round", 0)) or 1) if resume_stage != "Reflection" else round_number
		while round_number <= max_rounds:
			current["_round"] = round_number
			telemetry.emit("round_started", stage="core", message="round started", round=round_number)
			stage_order = ["Search", "Crawl", "Summarize", "Verify", "Reflection"]
			start_index = stage_order.index(next_stage) if next_stage in stage_order else 0
			for stage_name in stage_order[start_index:]:
				telemetry.start_stage(stage_name)
				if stage_name == "Search":
					current = run_search(current)
					telemetry.end_stage("Search", search_results=len(current.get("search_results", [])))
				elif stage_name == "Crawl":
					current = run_crawl(current)
					telemetry.end_stage("Crawl", documents=len(current.get("documents", [])))
				elif stage_name == "Summarize":
					current = run_summarize(current)
					telemetry.end_stage("Summarize", summaries=len(current.get("summaries", [])))
				elif stage_name == "Verify":
					current = run_verify(current)
					telemetry.end_stage("Verify", verified_results=len(current.get("verified_results", [])))
				elif stage_name == "Reflection":
					current = run_reflection(current)
					telemetry.end_stage("Reflection", should_continue=bool(current.get("reflection", {}).get("should_continue")))
				current["_workflow_stage"] = stage_name
				self._save_checkpoint(stage_name, current)
			self.snapshots.append(current.copy())
			reflection = current.get("reflection", {})
			should_continue = bool(reflection.get("should_continue"))
			next_stage = "Search"
			if not should_continue:
				break
			round_number += 1
		telemetry.finish()
		current["telemetry"] = telemetry.to_dict()
		final_answer = _build_final_answer(current.get("summaries", []), current.get("verified_results", []))
		bullet_summary = _build_bullet_summary(current.get("summaries", []))
		current["quality_control"] = evaluate_output_quality(
			current.get("summaries", []),
			current.get("verified_results", []),
			current.get("citations", []),
			final_answer,
			bullet_summary,
		)
		current["final_report"] = self.build_final_report(current)
		current["_workflow_stage"] = "Complete"
		self._save_checkpoint("Complete", current, is_final=True)
		return current

	def resume(self, run_id: str, user_query: str = "") -> ResearchState:
		return self.run(user_query=user_query, resume_run_id=run_id)

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
		telemetry = state.get("telemetry", {}) if isinstance(state.get("telemetry", {}), dict) else {}
		stage_durations = telemetry.get("stage_durations", {}) if isinstance(telemetry, dict) else {}
		stage_lines = [f"- {stage}: {duration:.3f}s" for stage, duration in stage_durations.items()]
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
			f"Run ID: {state.get('run_id', '')}",
			f"Rounds: {round_number}",
			f"Tasks completed: {len(tasks)}",
			f"Summaries generated: {len(summaries)}",
			f"Verified results: {len(verified_results)}",
			f"Elapsed seconds: {telemetry.get('elapsed_seconds', 0.0):.3f}" if isinstance(telemetry, dict) else "Elapsed seconds: 0.000",
			"",
			"Stage timings",
			*(stage_lines or ["- 暂无阶段计时"]),
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
			"",
			"6. 输出质量控制",
			f"- 评分: {state.get('quality_control', {}).get('score', 0)}/100",
			f"- 需要复核: {state.get('quality_control', {}).get('needs_review', False)}",
			*([f"- {issue}" for issue in state.get('quality_control', {}).get('issues', [])] or ["- 无明显问题"]),
		]
		return "\n".join(lines)
