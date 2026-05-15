from __future__ import annotations

import pytest

from services.model_adapter import (
	ClaudeModelAdapter,
	LocalModelAdapter,
	ModelMessage,
	OpenAIModelAdapter,
	create_model_adapter,
)


def test_create_model_adapter_defaults_to_local():
	adapter = create_model_adapter("local", "gpt-5.4-mini")

	assert isinstance(adapter, LocalModelAdapter)
	response = adapter.complete(
		[
			ModelMessage(role="system", content="You are helpful."),
			ModelMessage(role="user", content="Summarize this topic."),
		],
		system_prompt="System prompt.",
	)

	assert response.provider == "local"
	assert response.model == "gpt-5.4-mini"
	assert "System prompt." in response.content
	assert "Summarize this topic." in response.content


def test_create_model_adapter_recognizes_openai_and_claude():
	openai_adapter = create_model_adapter("openai", "gpt-4.1")
	claude_adapter = create_model_adapter("claude", "claude-sonnet-4")

	assert isinstance(openai_adapter, OpenAIModelAdapter)
	assert isinstance(claude_adapter, ClaudeModelAdapter)


def test_create_model_adapter_rejects_unknown_provider():
	with pytest.raises(ValueError, match="Unsupported model provider"):
		create_model_adapter("other", "model")