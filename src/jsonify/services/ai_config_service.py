"""Local persistence for the optional AI provider configuration.

Stored the same way as the rest of Jsonify's local state (a JSON file
under the app data directory) — nothing here is ever sent anywhere on its
own; ``services.ai_service`` is what actually calls out, and only when the
caller explicitly asks it to.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonify.core.ai_provider import AiProviderConfig
from jsonify.services.workspace_state_service import default_app_data_dir


class AiConfigService:
    """Stores the single active AI provider configuration."""

    def __init__(self, data_dir: Path | None = None) -> None:
        directory = data_dir if data_dir is not None else default_app_data_dir()
        self._path = directory / "ai_config.json"

    def get_config(self) -> AiProviderConfig:
        data = self._load()
        return AiProviderConfig(
            base_url=data.get("base_url", ""),
            api_key=data.get("api_key", ""),
            model=data.get("model", ""),
        )

    def set_config(self, config: AiProviderConfig) -> None:
        self._save(
            {"base_url": config.base_url, "api_key": config.api_key, "model": config.model}
        )

    def clear_config(self) -> None:
        self._save({"base_url": "", "api_key": "", "model": ""})

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        return raw if isinstance(raw, dict) else {}

    def _save(self, data: dict[str, Any]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
