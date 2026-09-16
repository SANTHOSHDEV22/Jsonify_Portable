"""Saved-session models for Jsonify."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jsonify.core.models import JSONValue


SESSION_FORMAT = "jsonify-session"
SESSION_VERSION = 1


@dataclass(slots=True)
class SessionWorkspace:
    """UI state that may be restored with a Jsonify session."""

    selected_tab: str = ""
    jsonpath_query: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert workspace state to serializable data."""

        return {
            "selected_tab": self.selected_tab,
            "jsonpath_query": self.jsonpath_query,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> SessionWorkspace:
        """Create workspace state from serialized data."""

        return cls(
            selected_tab=str(
                data.get("selected_tab", "")
            ),
            jsonpath_query=str(
                data.get("jsonpath_query", "")
            ),
        )


@dataclass(slots=True)
class JsonifySession:
    """Represents a saved Jsonify workspace."""

    name: str
    payload: JSONValue
    workspace: SessionWorkspace = field(
        default_factory=SessionWorkspace
    )
    created_at: str = field(
        default_factory=lambda: _utc_now()
    )
    updated_at: str = field(
        default_factory=lambda: _utc_now()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the session to serializable data."""

        return {
            "format": SESSION_FORMAT,
            "version": SESSION_VERSION,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payload": self.payload,
            "workspace": self.workspace.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> JsonifySession:
        """Create a session from serialized data."""

        workspace_data = data.get(
            "workspace",
            {},
        )

        if not isinstance(
            workspace_data,
            dict,
        ):
            workspace_data = {}

        return cls(
            name=str(
                data.get("name", "Untitled Session")
            ),
            payload=data.get("payload"),
            workspace=SessionWorkspace.from_dict(
                workspace_data
            ),
            created_at=str(
                data.get(
                    "created_at",
                    _utc_now(),
                )
            ),
            updated_at=str(
                data.get(
                    "updated_at",
                    _utc_now(),
                )
            ),
        )


def _utc_now() -> str:
    """Return the current UTC time as ISO 8601."""

    return datetime.now(
        timezone.utc
    ).isoformat()