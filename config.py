"""Configuration helpers for the webSearch workflow."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
	model_name: str = "gpt-5.4-mini"
	max_rounds: int = 3
	request_timeout: int = 20
	max_concurrency: int = 4
	user_agent: str = "webSearch/0.1"


def load_settings() -> Settings:
	return Settings(
		model_name=os.getenv("WEBSEARCH_MODEL_NAME", "gpt-5.4-mini"),
		max_rounds=int(os.getenv("WEBSEARCH_MAX_ROUNDS", "3")),
		request_timeout=int(os.getenv("WEBSEARCH_REQUEST_TIMEOUT", "20")),
		max_concurrency=int(os.getenv("WEBSEARCH_MAX_CONCURRENCY", "4")),
		user_agent=os.getenv("WEBSEARCH_USER_AGENT", "webSearch/0.1"),
	)


settings = load_settings()
