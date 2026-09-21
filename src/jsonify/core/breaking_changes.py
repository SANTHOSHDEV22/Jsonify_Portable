"""Classify a JSON diff into API-breaking vs. non-breaking changes.

Removed properties and type changes are always breaking. A newly added
property is only breaking if it's marked ``required`` by a JSON Schema for
the *new* document — an optional new field is additive and safe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from jsonify.core.diff import DiffType, JsonDiff, compare_json
from jsonify.core.models import JSONValue

_PATH_TOKEN = re.compile(r'\.([A-Za-z_][A-Za-z0-9_]*)|\["((?:[^"\\]|\\.)*)"\]|\[(\d+)\]')


@dataclass(frozen=True, slots=True)
class BreakingChange:
    """One API-breaking change detected between two JSON documents."""

    category: str  # "removed_property" | "type_changed" | "new_required_property"
    path: str
    detail: str


def detect_breaking_changes(
    old: JSONValue,
    new: JSONValue,
    *,
    new_schema: dict[str, Any] | None = None,
) -> list[BreakingChange]:
    """Diff ``old`` vs ``new`` and classify the breaking changes found."""

    diffs = compare_json(old, new)
    return classify_diff(diffs, new_schema=new_schema)


def classify_diff(
    diffs: list[JsonDiff],
    *,
    new_schema: dict[str, Any] | None = None,
) -> list[BreakingChange]:
    """Classify already-computed diffs into breaking changes."""

    changes: list[BreakingChange] = []

    for diff in diffs:
        if diff.diff_type == DiffType.REMOVED:
            changes.append(
                BreakingChange(
                    category="removed_property",
                    path=diff.path,
                    detail=f"Property was removed (previous value: {diff.old_value!r}).",
                )
            )
        elif diff.diff_type == DiffType.TYPE_CHANGED:
            changes.append(
                BreakingChange(
                    category="type_changed",
                    path=diff.path,
                    detail=f"Type changed from {diff.old_value!r} to {diff.new_value!r}.",
                )
            )
        elif diff.diff_type == DiffType.ADDED and new_schema is not None:
            if _is_required_at_path(new_schema, diff.path):
                changes.append(
                    BreakingChange(
                        category="new_required_property",
                        path=diff.path,
                        detail="A new property was added and is marked required by the schema.",
                    )
                )

    return changes


def _is_required_at_path(schema: dict[str, Any], path: str) -> bool:
    """Check whether the schema marks the final segment of ``path`` required."""

    segments = _parse_diff_path(path)
    if not segments:
        return False

    *ancestor_segments, final_key = segments
    if not isinstance(final_key, str):
        return False

    node = schema
    for segment in ancestor_segments:
        if isinstance(segment, int):
            node = node.get("items", {}) if isinstance(node, dict) else {}
        else:
            node = node.get("properties", {}).get(segment, {}) if isinstance(node, dict) else {}
        if not isinstance(node, dict):
            return False

    required = node.get("required", [])
    return isinstance(required, list) and final_key in required


def _parse_diff_path(path: str) -> list[str | int]:
    """Parse a ``$.a.b[0]["c d"]``-style diff path back into segments."""

    body = path[1:] if path.startswith("$") else path
    segments: list[str | int] = []

    for match in _PATH_TOKEN.finditer(body):
        dotted, bracketed, indexed = match.groups()
        if dotted is not None:
            segments.append(dotted)
        elif bracketed is not None:
            segments.append(bracketed.replace('\\"', '"').replace("\\\\", "\\"))
        elif indexed is not None:
            segments.append(int(indexed))

    return segments
