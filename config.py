"""Configuration helpers for the webSearch workflow."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
	model_provider: str = "local"
	model_name: str = "gpt-5.4-mini"
	max_rounds: int = 3
	request_timeout: int = 20
	max_concurrency: int = 4
	user_agent: str = "webSearch/0.1"
	dynamic_fetch_domains: list[str] = None  # type: ignore[assignment]


def load_settings() -> Settings:
	dynamic_fetch_domains = [
		domain.strip().lower()
		for domain in os.getenv("WEBSEARCH_DYNAMIC_FETCH_DOMAINS", "").split(",")
		if domain.strip()
	]
	return Settings(
		model_provider=os.getenv("WEBSEARCH_MODEL_PROVIDER", "local"),
		model_name=os.getenv("WEBSEARCH_MODEL_NAME", "gpt-5.4-mini"),
		max_rounds=int(os.getenv("WEBSEARCH_MAX_ROUNDS", "3")),
		request_timeout=int(os.getenv("WEBSEARCH_REQUEST_TIMEOUT", "20")),
		max_concurrency=int(os.getenv("WEBSEARCH_MAX_CONCURRENCY", "4")),
		user_agent=os.getenv("WEBSEARCH_USER_AGENT", "webSearch/0.1"),
		dynamic_fetch_domains=dynamic_fetch_domains,
	)


settings = load_settings()
