"""Large JSON optimization service."""

from __future__ import annotations

from dataclasses import dataclass

from jsonify.core.large_json import (
    JsonSizeInfo,
    analyze_json,
)
from jsonify.core.models import JSONValue


@dataclass(frozen=True, slots=True)
class LargeJsonSettings:
    """Configuration for large JSON rendering."""

    lazy_threshold: int = 10_000
    preview_length: int = 120
    array_page_size: int = 500


class LargeJsonService:
    """Provides large-payload analysis and rendering decisions."""

    def __init__(
        self,
        settings: LargeJsonSettings | None = None,
    ) -> None:
        self.settings = (
            settings
            if settings is not None
            else LargeJsonSettings()
        )

    def analyze(
        self,
        payload: JSONValue,
    ) -> JsonSizeInfo:
        """Analyze a JSON payload."""

        return analyze_json(payload)

    def should_use_lazy_tree(
        self,
        info: JsonSizeInfo,
    ) -> bool:
        """Return whether lazy tree rendering is recommended."""

        return (
            info.total_nodes
            >= self.settings.lazy_threshold
        )

    def preview(
        self,
        value: JSONValue,
    ) -> str:
        """Create a short value preview."""

        if isinstance(value, dict):
            return f"Object ({len(value)} properties)"

        if isinstance(value, list):
            return f"Array ({len(value)} items)"

        if value is None:
            return "null"

        if isinstance(value, bool):
            return (
                "true"
                if value
                else "false"
            )

        text = str(value)

        limit = self.settings.preview_length

        if len(text) > limit:
            return (
                text[:limit]
                + "..."
            )

        return text