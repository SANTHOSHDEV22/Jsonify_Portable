"""Tests for local persistence of the AI provider configuration."""

from __future__ import annotations

from pathlib import Path

from jsonify.core.ai_provider import AiProviderConfig
from jsonify.services.ai_config_service import AiConfigService


def test_default_config_is_empty(tmp_path: Path) -> None:
    config = AiConfigService(tmp_path).get_config()

    assert config == AiProviderConfig()
    assert config.is_configured is False


def test_set_config_persists_across_instances(tmp_path: Path) -> None:
    saved = AiProviderConfig(base_url="http://localhost:11434/v1", api_key="", model="llama3")
    AiConfigService(tmp_path).set_config(saved)

    loaded = AiConfigService(tmp_path).get_config()

    assert loaded == saved


def test_clear_config_resets_to_empty(tmp_path: Path) -> None:
    service = AiConfigService(tmp_path)
    service.set_config(AiProviderConfig(base_url="https://api.openai.com/v1", model="gpt-4o-mini"))

    service.clear_config()

    assert service.get_config() == AiProviderConfig()


def test_corrupt_file_falls_back_to_default(tmp_path: Path) -> None:
    (tmp_path / "ai_config.json").write_text("not json", encoding="utf-8")

    assert AiConfigService(tmp_path).get_config() == AiProviderConfig()
