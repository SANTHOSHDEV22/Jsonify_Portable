"""Local persistence for API history, collections, and environments."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonify.core.api_request import ApiRequest
from jsonify.services.workspace_state_service import default_app_data_dir

DEFAULT_ENVIRONMENTS = ("Dev", "Test", "QA", "Prod")
HISTORY_LIMIT = 50
_BODY_LIMIT = 200_000


class ApiWorkspaceService:
    """Stores request history, saved collections, and environment variables."""

    def __init__(self, data_dir: Path | None = None) -> None:
        directory = data_dir if data_dir is not None else default_app_data_dir()
        self._path = directory / "api_workspace.json"

    # -----------------------------------------------------------------
    # History
    # -----------------------------------------------------------------

    def get_history(self) -> list[dict[str, Any]]:
        """Return history entries, newest first."""

        return list(self._load()["history"])

    def add_history(
        self,
        request: ApiRequest,
        *,
        status_code: int,
        elapsed_ms: float,
        size_bytes: int,
        body: str,
    ) -> None:
        """Record a completed request/response."""

        data = self._load()
        entry = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "request": request.to_dict(),
            "status": status_code,
            "elapsed_ms": round(elapsed_ms, 1),
            "size_bytes": size_bytes,
            "body": body[:_BODY_LIMIT],
        }
        data["history"] = [entry, *data["history"]][:HISTORY_LIMIT]
        self._save(data)

    def clear_history(self) -> None:
        data = self._load()
        data["history"] = []
        self._save(data)

    # -----------------------------------------------------------------
    # Collections
    # -----------------------------------------------------------------

    def get_collections(self) -> dict[str, list[dict[str, Any]]]:
        """Return ``{collection name: [{"name": ..., "request": {...}}]}``."""

        return dict(self._load()["collections"])

    def save_to_collection(self, collection: str, name: str, request: ApiRequest) -> None:
        """Save (or overwrite by name) a request inside a collection."""

        data = self._load()
        items = [i for i in data["collections"].get(collection, []) if i.get("name") != name]
        items.append({"name": name, "request": request.to_dict()})
        data["collections"][collection] = items
        self._save(data)

    def delete_from_collection(self, collection: str, name: str) -> None:
        data = self._load()
        items = [i for i in data["collections"].get(collection, []) if i.get("name") != name]
        if items:
            data["collections"][collection] = items
        else:
            data["collections"].pop(collection, None)
        self._save(data)

    # -----------------------------------------------------------------
    # Environments
    # -----------------------------------------------------------------

    def get_environments(self) -> dict[str, dict[str, str]]:
        return {name: dict(values) for name, values in self._load()["environments"].items()}

    def set_environment(self, name: str, variables: dict[str, str]) -> None:
        data = self._load()
        data["environments"][name] = {str(k): str(v) for k, v in variables.items()}
        self._save(data)

    def get_active_environment(self) -> str:
        data = self._load()
        active = data.get("active_environment", DEFAULT_ENVIRONMENTS[0])
        return active if active in data["environments"] else DEFAULT_ENVIRONMENTS[0]

    def set_active_environment(self, name: str) -> None:
        data = self._load()
        data["active_environment"] = name
        self._save(data)

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}

        if not isinstance(raw, dict):
            raw = {}

        environments = raw.get("environments")
        if not isinstance(environments, dict) or not environments:
            environments = {name: {} for name in DEFAULT_ENVIRONMENTS}

        return {
            "history": raw.get("history") if isinstance(raw.get("history"), list) else [],
            "collections": raw.get("collections")
            if isinstance(raw.get("collections"), dict)
            else {},
            "environments": environments,
            "active_environment": raw.get("active_environment", DEFAULT_ENVIRONMENTS[0]),
        }

    def _save(self, data: dict[str, Any]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
