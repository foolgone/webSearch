"""Summarize agent."""

from __future__ import annotations

from models import ResearchState
from config import settings
from services.model_adapter import ModelMessage, create_model_adapter


def _split_sentences(content: str) -> list[str]:
	parts = [segment.strip() for segment in content.replace("\n", " ").split(".")]
	return [part for part in parts if part]


def run_summarize(state: ResearchState) -> ResearchState:
	documents = state.get("documents", [])
	summaries: list[dict[str, str | list[str]]] = []
	adapter = create_model_adapter(settings.model_provider, settings.model_name)

	for document in documents:
		content = document.get("content", "").strip()
		title = document.get("title", "").strip()
		response = adapter.complete(
			[
				ModelMessage(role="user", content=f"TITLE: {title}\nCONTENT: {content}"),
			],
			system_prompt="Summarize agent",
		)
		payload = response.raw if isinstance(response.raw, dict) else {}
		bullets = list(payload.get("bullets", []))
		if not bullets:
			sentences = _split_sentences(content)
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
				"short_summary": payload.get("short_summary", " ".join(bullets[:2])),
			}
		)

	state["summaries"] = summaries
	return state
