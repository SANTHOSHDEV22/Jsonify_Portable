"""Saved-session service for Jsonify."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonify.core.models import JSONValue
from jsonify.core.session import (
    SESSION_FORMAT,
    SESSION_VERSION,
    JsonifySession,
    SessionWorkspace,
)


class SessionError(ValueError):
    """Raised when a Jsonify session cannot be loaded or saved."""


class SessionService:
    """Provides local Jsonify session persistence."""

    FILE_EXTENSION = ".jsonify"

    def create_session(
        self,
        *,
        name: str,
        payload: JSONValue,
        selected_tab: str = "",
        jsonpath_query: str = "",
        bookmarks: list[str] | None = None,
        annotations: dict[str, str] | None = None,
    ) -> JsonifySession:
        """Create a new in-memory session."""

        clean_name = name.strip()

        if not clean_name:
            clean_name = "Untitled Session"

        now = self._utc_now()

        return JsonifySession(
            name=clean_name,
            payload=payload,
            workspace=SessionWorkspace(
                selected_tab=selected_tab,
                jsonpath_query=jsonpath_query,
                bookmarks=list(bookmarks or []),
                annotations=dict(annotations or {}),
            ),
            created_at=now,
            updated_at=now,
        )

    def save(
        self,
        session: JsonifySession,
        file_path: str | Path,
    ) -> Path:
        """Save a Jsonify session to disk."""

        path = Path(file_path)

        if path.suffix.lower() != self.FILE_EXTENSION:
            path = path.with_suffix(self.FILE_EXTENSION)

        session.updated_at = self._utc_now()

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_text(
                json.dumps(
                    session.to_dict(),
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        except OSError as error:
            raise SessionError(f"Unable to save session: {error}") from error

        return path

    def load(
        self,
        file_path: str | Path,
    ) -> JsonifySession:
        """Load and validate a Jsonify session."""

        path = Path(file_path)

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            raise SessionError(f"Unable to open session: {error}") from error

        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise SessionError("The selected file is not valid JSON.") from error

        if not isinstance(data, dict):
            raise SessionError("Invalid Jsonify session file.")

        self._validate_session_data(data)

        return JsonifySession.from_dict(data)

    @staticmethod
    def _validate_session_data(
        data: dict[str, Any],
    ) -> None:
        """Validate session metadata."""

        if data.get("format") != SESSION_FORMAT:
            raise SessionError("This file is not a Jsonify session.")

        version = data.get("version")

        if version != SESSION_VERSION:
            raise SessionError(f"Unsupported Jsonify session version: {version}")

        if "payload" not in data:
            raise SessionError("The session does not contain a JSON payload.")

    @staticmethod
    def _utc_now() -> str:
        """Return current UTC time."""

        return datetime.now(UTC).isoformat()
