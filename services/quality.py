"""Final output quality control helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


GENERIC_UNSUPPORTED_PHRASES = (
	"No extractable content found.",
	"No summary bullets could be matched to the source document.",
	"当前证据不足",
	"暂无来源链接",
	"暂无 citation",
)


def _extract_summary_urls(summaries: list[dict[str, Any]]) -> list[str]:
	urls: list[str] = []
	for summary in summaries:
		url = str(summary.get("url", "")).strip()
		if url:
			urls.append(url)
	return urls


def evaluate_output_quality(
	summaries: list[dict[str, Any]],
	verified_results: list[dict[str, Any]],
	citations: list[dict[str, Any]],
	final_answer: list[str],
	bullet_summary: list[str],
) -> dict[str, Any]:
	"""Score the final answer for traceability and content hygiene."""

	issues: list[str] = []
	checks: dict[str, bool] = {}

	citation_urls = {str(item.get("url", "")).strip() for item in citations if str(item.get("url", "")).strip()}
	summary_urls = _extract_summary_urls(summaries)
	verified_by_url: dict[str, set[str]] = defaultdict(set)
	for item in verified_results:
		url = str(item.get("url", "")).strip()
		status = str(item.get("status", "")).strip().lower()
		if url:
			verified_by_url[url].add(status)

	selected_summary_urls: list[str] = []
	for line in final_answer:
		for summary in summaries:
			url = str(summary.get("url", "")).strip()
			if not url:
				continue
			bullets = summary.get("bullets", [])
			if not isinstance(bullets, list):
				continue
			if any(str(bullet).strip() and str(bullet).strip() in line for bullet in bullets[:2]):
				selected_summary_urls.append(url)

	checks["final_answer_present"] = any(line.strip() for line in final_answer)
	checks["citations_present"] = bool(citation_urls)
	checks["summary_links_covered"] = not selected_summary_urls or all(url in citation_urls for url in selected_summary_urls)
	checks["no_source_conflicts"] = all(len(statuses) <= 1 for statuses in verified_by_url.values())
	checks["has_supported_evidence"] = any(
		str(item.get("status", "")).lower() in {"passed", "partial"}
		for item in verified_results
	)
	checks["no_placeholder_text"] = not any(
		phrase in "\n".join([*final_answer, *bullet_summary])
		for phrase in GENERIC_UNSUPPORTED_PHRASES
	)
	checks["summary_count"] = bool(summary_urls)

	if not checks["final_answer_present"]:
		issues.append("final answer is empty")
	if not checks["citations_present"]:
		issues.append("no citations available")
	if not checks["summary_links_covered"]:
		issues.append("final answer references summaries without matching citations")
	if not checks["no_source_conflicts"]:
		issues.append("conflicting verification statuses detected for the same URL")
	if not checks["has_supported_evidence"]:
		issues.append("no supported evidence found in verified results")
	if not checks["no_placeholder_text"]:
		issues.append("placeholder-like fallback text detected in output")
	if not checks["summary_count"]:
		issues.append("no summaries available for final response")

	true_checks = sum(1 for value in checks.values() if value)
	max_checks = len(checks)
	score = int(round((true_checks / max_checks) * 100)) if max_checks else 0
	needs_review = score < 80 or bool(issues)
	return {
		"score": score,
		"needs_review": needs_review,
		"issues": issues,
		"checks": checks,
	}