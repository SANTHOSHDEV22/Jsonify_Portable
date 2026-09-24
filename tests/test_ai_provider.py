"""Tests for the AI provider config model."""

from __future__ import annotations

from jsonify.core.ai_provider import AiProviderConfig


def test_default_config_is_not_configured() -> None:
    assert AiProviderConfig().is_configured is False


def test_missing_model_is_not_configured() -> None:
    assert AiProviderConfig(base_url="https://api.openai.com/v1").is_configured is False


def test_missing_base_url_is_not_configured() -> None:
    assert AiProviderConfig(model="gpt-4o-mini").is_configured is False


def test_base_url_and_model_is_configured() -> None:
    config = AiProviderConfig(base_url="https://api.openai.com/v1", model="gpt-4o-mini")

    assert config.is_configured is True


def test_api_key_is_not_required_for_local_servers() -> None:
    config = AiProviderConfig(base_url="http://localhost:11434/v1", model="llama3")

    assert config.is_configured is True
    assert config.api_key == ""


def test_chat_completions_url_strips_trailing_slash() -> None:
    config = AiProviderConfig(base_url="https://api.openai.com/v1/", model="x")

    assert config.chat_completions_url() == "https://api.openai.com/v1/chat/completions"


def test_chat_completions_url_without_trailing_slash() -> None:
    config = AiProviderConfig(base_url="http://localhost:11434/v1", model="x")

    assert config.chat_completions_url() == "http://localhost:11434/v1/chat/completions"
