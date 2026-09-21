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

    # Hierarchy View renders as one big plain-text string (with
    # box-drawing tree connectors for every single node) rather than a
    # lazy/virtualized tree, so it's considerably more expensive per
    # node than the Normal View tab. This limit is intentionally much
    # lower than lazy_threshold: past this many nodes, the hierarchy
    # view shows a size summary instead of attempting a full render,
    # to keep the UI responsive.
    hierarchy_preview_nodes: int = 2_000


class LargeJsonService:
    """Provides large-payload analysis and rendering decisions."""

    def __init__(
        self,
        settings: LargeJsonSettings | None = None,
    ) -> None:
        self.settings = settings if settings is not None else LargeJsonSettings()

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

        return info.total_nodes >= self.settings.lazy_threshold

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
            return "true" if value else "false"

        text = str(value)

        limit = self.settings.preview_length

        if len(text) > limit:
            return text[:limit] + "..."

        return text
