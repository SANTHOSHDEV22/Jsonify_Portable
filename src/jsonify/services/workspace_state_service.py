"""Local persistence for cross-session UI state.

Stores small pieces of state outside of any single JSON document: recently
opened files, a crash-recovery snapshot of unsaved open tabs, and general
settings such as the selected theme. All of it lives as plain JSON files
under the user's home directory so it survives application restarts
without needing a database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonify.core.app_paths import data_dir


def default_app_data_dir() -> Path:
    """Return (and create) Jsonify's per-user local data directory."""

    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


class WorkspaceStateService:
    """Persists recent files and crash-recovery snapshots as local JSON."""

    RECENT_FILES_LIMIT = 10

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir if data_dir is not None else default_app_data_dir()
        self._recent_files_path = self._data_dir / "recent_files.json"
        self._recovery_path = self._data_dir / "recovery.json"
        self._settings_path = self._data_dir / "settings.json"

    # -----------------------------------------------------------------
    # Recent files
    # -----------------------------------------------------------------

    def get_recent_files(self) -> list[str]:
        """Return recently opened file paths, most recent first."""

        data = self._read_json(self._recent_files_path)

        if not isinstance(data, list):
            return []

        return [str(entry) for entry in data if isinstance(entry, str)]

    def add_recent_file(self, file_path: str | Path) -> None:
        """Record a file as recently opened."""

        path_str = str(file_path)
        existing = [p for p in self.get_recent_files() if p != path_str]
        updated = [path_str, *existing][: self.RECENT_FILES_LIMIT]
        self._write_json(self._recent_files_path, updated)

    def clear_recent_files(self) -> None:
        """Forget all recently opened files."""

        self._write_json(self._recent_files_path, [])

    # -----------------------------------------------------------------
    # Crash recovery
    # -----------------------------------------------------------------

    def write_recovery_snapshot(self, documents: list[dict[str, Any]]) -> None:
        """Persist the currently open documents for crash recovery."""

        self._write_json(self._recovery_path, documents)

    def read_recovery_snapshot(self) -> list[dict[str, Any]]:
        """Return the last crash-recovery snapshot, if any."""

        data = self._read_json(self._recovery_path)

        if not isinstance(data, list):
            return []

        return [entry for entry in data if isinstance(entry, dict)]

    def has_recovery_snapshot(self) -> bool:
        """Return whether a crash-recovery snapshot exists."""

        return self._recovery_path.exists() and bool(self.read_recovery_snapshot())

    def clear_recovery_snapshot(self) -> None:
        """Delete the crash-recovery snapshot (called on clean shutdown)."""

        try:
            self._recovery_path.unlink()
        except FileNotFoundError:
            pass

    # -----------------------------------------------------------------
    # Settings (theme, and future general preferences)
    # -----------------------------------------------------------------

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Return a single persisted setting value."""

        data = self._read_json(self._settings_path)

        if not isinstance(data, dict) or key not in data:
            return default

        return data[key]

    def set_setting(self, key: str, value: Any) -> None:
        """Persist a single setting value."""

        data = self._read_json(self._settings_path)

        if not isinstance(data, dict):
            data = {}

        data[key] = value
        self._write_json(self._settings_path, data)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
