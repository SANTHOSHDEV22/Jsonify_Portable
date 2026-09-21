"""Conversions between a path (list of keys/indices) and text notations.

A "path" here is the same segment list produced while walking a JSON tree:
each segment is either a ``str`` (an object key) or an ``int`` (an array
index). This module turns that segment list into either a JSONPath-style
string (``$.a.b[0]``) or an RFC 6901 JSON Pointer (``/a/b/0``).
"""

from __future__ import annotations

import re

PathSegment = str | int

_SIMPLE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def to_json_path(segments: list[PathSegment]) -> str:
    """Render segments as a JSONPath expression, e.g. ``$.a.b[0].c``."""

    parts = ["$"]

    for segment in segments:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        elif _SIMPLE_IDENTIFIER.match(segment):
            parts.append(f".{segment}")
        else:
            escaped = segment.replace("'", "\\'")
            parts.append(f"['{escaped}']")

    return "".join(parts)


def to_json_pointer(segments: list[PathSegment]) -> str:
    """Render segments as an RFC 6901 JSON Pointer, e.g. ``/a/b/0/c``."""

    if not segments:
        return ""

    tokens = [_escape_pointer_token(str(segment)) for segment in segments]
    return "/" + "/".join(tokens)


def _escape_pointer_token(token: str) -> str:
    """Escape ``~`` and ``/`` per RFC 6901 (``~`` -> ``~0``, ``/`` -> ``~1``)."""

    return token.replace("~", "~0").replace("/", "~1")


def from_json_pointer(pointer: str) -> list[PathSegment]:
    """Parse an RFC 6901 JSON Pointer back into segments.

    Numeric tokens are returned as ``int`` (array indices); everything
    else is returned as ``str`` (object keys). The empty string and ``"/"``
    both mean "no path" and return an empty list.
    """

    if not pointer or pointer == "/":
        return []

    if not pointer.startswith("/"):
        raise ValueError("A JSON Pointer must start with '/'.")

    segments: list[PathSegment] = []

    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")

        if token.isdigit() and (token == "0" or not token.startswith("0")):
            segments.append(int(token))
        else:
            segments.append(token)

    return segments
