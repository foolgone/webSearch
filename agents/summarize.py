"""Summarize agent."""

from __future__ import annotations

from models import ResearchState


def _split_sentences(content: str) -> list[str]:
	parts = [segment.strip() for segment in content.replace("\n", " ").split(".")]
	return [part for part in parts if part]


def run_summarize(state: ResearchState) -> ResearchState:
	documents = state.get("documents", [])
	summaries: list[dict[str, str | list[str]]] = []

	for document in documents:
		content = document.get("content", "").strip()
		title = document.get("title", "").strip()
		sentences = _split_sentences(content)
		bullets: list[str] = []

		if title:
			bullets.append(f"Title: {title}")
		if sentences:
			bullets.extend(sentences[:3])
		elif content:
			bullets.append(content[:280])
		else:
			bullets.append("No extractable content found.")

		summaries.append(
			{
				"url": document.get("url", ""),
				"bullets": bullets,
				"short_summary": " ".join(bullets[:2]),
			}
		)

	state["summaries"] = summaries
	return state
