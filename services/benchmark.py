"""Fixed benchmark suite for regression and output quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from orchestrator import Orchestrator


SECTION_HEADERS = (
	"1. 最终答案",
	"2. 分点总结",
	"3. Citation",
	"4. 来源链接",
	"5. 推理依据",
)


@dataclass(slots=True, frozen=True)
class BenchmarkCase:
	name: str
	query: str
	min_score: int = 70


@dataclass(slots=True)
class BenchmarkResult:
	case: BenchmarkCase
	score: int
	checks: dict[str, bool] = field(default_factory=dict)
	state: dict[str, Any] = field(default_factory=dict)


DEFAULT_BENCHMARK_CASES: tuple[BenchmarkCase, ...] = (
	BenchmarkCase(name="workflow-overview", query="webSearch 的当前流程是怎样的？"),
	BenchmarkCase(name="evidence-traceability", query="如何判断答案是否有足够引用支持？"),
	BenchmarkCase(name="product-readiness", query="这个原型还缺哪些产品化能力？"),
)


def _score_state(state: dict[str, Any]) -> tuple[int, dict[str, bool]]:
	report = str(state.get("final_report", ""))
	telemetry = state.get("telemetry", {})
	stage_durations = telemetry.get("stage_durations", {}) if isinstance(telemetry, dict) else {}
	citations = state.get("citations", [])
	documents = state.get("documents", [])
	summaries = state.get("summaries", [])

	checks = {
		"sections_present": all(header in report for header in SECTION_HEADERS),
		"report_non_empty": bool(report.strip()),
		"citations_present": bool(citations),
		"documents_present": bool(documents),
		"summaries_present": bool(summaries),
		"telemetry_present": isinstance(telemetry, dict) and bool(stage_durations),
		"all_core_stages_timed": isinstance(stage_durations, dict)
		and all(stage in stage_durations for stage in ["Planner", "Search", "Crawl", "Summarize", "Verify", "Reflection"]),
	}

	score = 0
	score += 35 if checks["sections_present"] else 0
	score += 15 if checks["report_non_empty"] else 0
	score += 15 if checks["citations_present"] else 0
	score += 10 if checks["documents_present"] else 0
	score += 10 if checks["summaries_present"] else 0
	score += 15 if checks["all_core_stages_timed"] else 0
	return score, checks


def run_benchmark(
	cases: Iterable[BenchmarkCase] = DEFAULT_BENCHMARK_CASES,
	orchestrator_factory: Callable[[], Orchestrator] = Orchestrator,
) -> list[BenchmarkResult]:
	results: list[BenchmarkResult] = []
	for case in cases:
		orchestrator = orchestrator_factory()
		state = orchestrator.run(case.query)
		score, checks = _score_state(state)
		results.append(BenchmarkResult(case=case, score=score, checks=checks, state=state))
	return results


def format_benchmark_report(results: Iterable[BenchmarkResult]) -> str:
	lines = ["Benchmark Report", ""]
	result_list = list(results)
	if not result_list:
		return "Benchmark Report\n\nNo benchmark cases were executed."

	passed = 0
	for index, result in enumerate(result_list, start=1):
		passed += int(result.score >= result.case.min_score)
		lines.append(f"{index}. {result.case.name}")
		lines.append(f"   Query: {result.case.query}")
		lines.append(f"   Score: {result.score}/100 (threshold: {result.case.min_score})")
		for check_name, ok in result.checks.items():
			lines.append(f"   - {check_name}: {ok}")
		lines.append("")
	lines.append(f"Passed: {passed}/{len(result_list)}")
	lines.append(f"Average score: {sum(result.score for result in result_list) / len(result_list):.1f}/100")
	return "\n".join(lines).rstrip()