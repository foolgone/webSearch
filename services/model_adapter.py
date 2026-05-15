"""Unified model adapter entry point for future OpenAI or Claude integrations."""

from __future__ import annotations

import json
from dataclasses import dataclass
import re
from typing import Any, Protocol, Sequence


@dataclass(slots=True)
class ModelMessage:
	role: str
	content: str


@dataclass(slots=True)
class ModelResponse:
	provider: str
	model: str
	content: str
	raw: Any | None = None


class ModelAdapter(Protocol):
	provider_name: str
	model_name: str

	def complete(
		self,
		messages: Sequence[ModelMessage],
		*,
		system_prompt: str = "",
		temperature: float = 0.0,
	) -> ModelResponse:
		...


@dataclass(slots=True)
class LocalModelAdapter:
	"""Deterministic offline adapter used until a real provider is wired in."""

	model_name: str = "local"
	provider_name: str = "local"

	def complete(
		self,
		messages: Sequence[ModelMessage],
		*,
		system_prompt: str = "",
		temperature: float = 0.0,
	) -> ModelResponse:
		last_user_message = next((message.content for message in reversed(messages) if message.role == "user"), "")
		system_prompt_lower = system_prompt.lower()

		if "planner" in system_prompt_lower:
			query = last_user_message.strip()
			payload = {
				"tasks": [
					f"Understand the research question: {query}" if query else "Understand the research question.",
					"Find relevant sources",
					"Summarize the sources",
					"Verify the evidence",
				],
				"search_queries": [query] if query else [],
			}
			return ModelResponse(
				provider=self.provider_name,
				model=self.model_name,
				content=json.dumps(payload, ensure_ascii=False),
				raw=payload,
			)

		if "summarize" in system_prompt_lower:
			title_match = re.search(r"^TITLE:\s*(.*)$", last_user_message, flags=re.MULTILINE)
			content_match = re.search(r"^CONTENT:\s*(.*)$", last_user_message, flags=re.MULTILINE | re.DOTALL)
			title = title_match.group(1).strip() if title_match else ""
			content = content_match.group(1).strip() if content_match else last_user_message.strip()
			segments = [segment.strip() for segment in content.replace("\n", " ").split(".")]
			bullets: list[str] = []
			if title:
				bullets.append(f"Title: {title}")
			if segments and any(segments):
				bullets.extend([segment for segment in segments if segment][:3])
			elif content:
				bullets.append(content[:280])
			else:
				bullets.append("No extractable content found.")
			payload = {
				"bullets": bullets,
				"short_summary": " ".join(bullets[:2]),
			}
			return ModelResponse(
				provider=self.provider_name,
				model=self.model_name,
				content=json.dumps(payload, ensure_ascii=False),
				raw=payload,
			)

		if "reflection" in system_prompt_lower:
			failed_count_match = re.search(r"^TOTAL_FAILED:\s*(\d+)$", last_user_message, flags=re.MULTILINE)
			failed_urls_match = re.search(r"^FAILED_URLS:\s*(.*)$", last_user_message, flags=re.MULTILINE)
			failed_count = int(failed_count_match.group(1)) if failed_count_match else 0
			failed_urls_raw = failed_urls_match.group(1).strip() if failed_urls_match else ""
			failed_urls = [url.strip() for url in failed_urls_raw.split("|") if url.strip()]
			payload = {
				"gap": f"{failed_count} item(s) need more evidence." if failed_count else "No major evidence gaps detected.",
				"next_action": "Refine search queries and re-run crawl." if failed_count else "Finalize the report.",
				"should_continue": bool(failed_count),
				"failed_urls": failed_urls,
			}
			return ModelResponse(
				provider=self.provider_name,
				model=self.model_name,
				content=json.dumps(payload, ensure_ascii=False),
				raw=payload,
			)

		parts = [segment.strip() for segment in [system_prompt, last_user_message] if segment.strip()]
		content = "\n".join(parts) if parts else "Local model adapter placeholder response."
		return ModelResponse(provider=self.provider_name, model=self.model_name, content=content)


@dataclass(slots=True)
class OpenAIModelAdapter:
	model_name: str
	provider_name: str = "openai"

	def complete(
		self,
		messages: Sequence[ModelMessage],
		*,
		system_prompt: str = "",
		temperature: float = 0.0,
	) -> ModelResponse:
		raise NotImplementedError("OpenAI adapter is not wired yet. Use LocalModelAdapter for offline runs.")


@dataclass(slots=True)
class ClaudeModelAdapter:
	model_name: str
	provider_name: str = "claude"

	def complete(
		self,
		messages: Sequence[ModelMessage],
		*,
		system_prompt: str = "",
		temperature: float = 0.0,
	) -> ModelResponse:
		raise NotImplementedError("Claude adapter is not wired yet. Use LocalModelAdapter for offline runs.")


def create_model_adapter(provider: str, model_name: str) -> ModelAdapter:
	normalized_provider = provider.strip().lower()
	if normalized_provider in {"", "local", "stub", "offline"}:
		return LocalModelAdapter(model_name=model_name)
	if normalized_provider == "openai":
		return OpenAIModelAdapter(model_name=model_name)
	if normalized_provider == "claude":
		return ClaudeModelAdapter(model_name=model_name)
	raise ValueError(f"Unsupported model provider: {provider}")