"""Core licensing models for Jsonify."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LicenseTier(StrEnum):
    """Available Jsonify license tiers."""

    FREE = "free"
    PRO = "pro"


class Feature(StrEnum):
    """Features that may be controlled by licensing."""

    JSON_VIEWER = "json_viewer"
    TREE_VIEW = "tree_view"
    HIERARCHY = "hierarchy"
    BASIC_GRAPH = "basic_graph"
    FILTERING = "filtering"

    JSON_DIFF = "json_diff"
    JSONPATH = "jsonpath"
    SCHEMA_VALIDATION = "schema_validation"
    DATA_MASKING = "data_masking"
    SAVED_SESSIONS = "saved_sessions"
    API_VIEWER = "api_viewer"
    EXPORT = "export"
    LARGE_JSON = "large_json"
    ADVANCED_GRAPH = "advanced_graph"


FREE_FEATURES: frozenset[Feature] = frozenset(
    {
        Feature.JSON_VIEWER,
        Feature.TREE_VIEW,
        Feature.HIERARCHY,
        Feature.BASIC_GRAPH,
        Feature.FILTERING,
    }
)


PRO_FEATURES: frozenset[Feature] = frozenset(
    set(Feature) - FREE_FEATURES
)


@dataclass(frozen=True, slots=True)
class LicenseInfo:
    """Current Jsonify license information."""

    tier: LicenseTier
    licensed_to: str = ""
    license_id: str = ""
    expires_at: str | None = None

    @property
    def is_pro(self) -> bool:
        """Return whether this is a Pro license."""

        return self.tier == LicenseTier.PRO