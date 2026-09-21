"""Search across a JSON document's keys and/or values.

Returns path segments (the same ``str | int`` segment lists used by
``jsonify.core.pointer``) for every match, in document order, so callers
can drive "next match" / "previous match" navigation and also render the
match as a JSONPath or JSON Pointer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from jsonify.core.models import JSONValue
from jsonify.core.pointer import PathSegment

SearchTarget = Literal["key", "value", "both"]


@dataclass(slots=True)
class SearchMatch:
    """One key or value that matched a search query."""

    segments: list[PathSegment]
    matched_key: bool
    matched_value: bool


def search_json(
    data: JSONValue,
    query: str,
    *,
    target: SearchTarget = "both",
    case_sensitive: bool = False,
    use_regex: bool = False,
) -> list[SearchMatch]:
    """Find every key and/or value in ``data`` that matches ``query``."""

    if not query:
        return []

    matcher = _build_matcher(query, case_sensitive=case_sensitive, use_regex=use_regex)
    if matcher is None:
        return []

    matches: list[SearchMatch] = []
    _walk(data, [], target, matcher, matches)
    return matches


def _build_matcher(query: str, *, case_sensitive: bool, use_regex: bool):
    if use_regex:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(query, flags)
        except re.error:
            return None
        return lambda text: pattern.search(text) is not None

    needle = query if case_sensitive else query.lower()

    def substring_match(text: str) -> bool:
        haystack = text if case_sensitive else text.lower()
        return needle in haystack

    return substring_match


def _walk(
    node: JSONValue,
    segments: list[PathSegment],
    target: SearchTarget,
    matcher,
    matches: list[SearchMatch],
) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            child_segments = [*segments, key]

            matched_key = target in ("key", "both") and matcher(key)
            matched_value = target in ("value", "both") and _leaf_matches(value, matcher)

            if matched_key or matched_value:
                matches.append(
                    SearchMatch(
                        segments=child_segments,
                        matched_key=matched_key,
                        matched_value=matched_value,
                    )
                )

            _walk(value, child_segments, target, matcher, matches)

    elif isinstance(node, list):
        for index, item in enumerate(node):
            child_segments = [*segments, index]

            matched_value = target in ("value", "both") and _leaf_matches(item, matcher)
            if matched_value:
                matches.append(
                    SearchMatch(segments=child_segments, matched_key=False, matched_value=True)
                )

            _walk(item, child_segments, target, matcher, matches)


def _leaf_matches(value: JSONValue, matcher) -> bool:
    if isinstance(value, dict | list):
        return False
    text = "null" if value is None else str(value)
    return matcher(text)
