"""Verify agent."""

from __future__ import annotations

from models import ResearchState


def _evidence_matches(summary: dict[str, object], document: dict[str, object]) -> tuple[str, str]:
	doc_content = str(document.get("content", "")).lower()
	doc_title = str(document.get("title", "")).lower()
	bullets = summary.get("bullets", [])
	if not isinstance(bullets, list):
		bullets = []

	matched = 0
	for bullet in bullets:
		bullet_text = str(bullet).strip().lower()
		if bullet_text.startswith("title: "):
			candidate_title = bullet_text.removeprefix("title: ").strip()
			if candidate_title and (candidate_title in doc_title or candidate_title in doc_content):
				matched += 1
			continue
		if bullet_text and bullet_text in doc_content:
			matched += 1

	if not bullets:
		return "partial", "No bullets to verify."
	if matched == len(bullets):
		return "passed", "All summary bullets are supported by the source document."
	if matched > 0:
		return "partial", f"{matched}/{len(bullets)} bullets matched the source document."
	return "failed", "No summary bullets could be matched to the source document."


def run_verify(state: ResearchState) -> ResearchState:
	summaries = state.get("summaries", [])
	documents = {document.get("url", ""): document for document in state.get("documents", [])}
	verified_results: list[dict[str, str]] = []
	citations: list[dict[str, str]] = []

	for summary in summaries:
		url = str(summary.get("url", ""))
		document = documents.get(url, {})
		status, notes = _evidence_matches(summary, document)
		verified_results.append(
			{
				"url": url,
				"status": status,
				"notes": notes,
			}
		)
		citations.append(
			{
				"url": url,
				"location": "body",
				"note": notes,
			}
		)

	state["verified_results"] = verified_results
	state["citations"] = citations
	return state
