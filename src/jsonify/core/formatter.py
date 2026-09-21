"""JSON formatting: beautify, minify, and key normalization."""

from __future__ import annotations

import json

from jsonify.core.models import JSONValue


def beautify(data: JSONValue, *, indent: int = 2, sort_keys: bool = False) -> str:
    """Pretty-print JSON with the given indent width."""

    return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)


def minify(data: JSONValue) -> str:
    """Render JSON with no unnecessary whitespace."""

    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def normalize(data: JSONValue) -> JSONValue:
    """Recursively sort object keys for a stable, comparable structure."""

    if isinstance(data, dict):
        return {key: normalize(data[key]) for key in sorted(data)}

    if isinstance(data, list):
        return [normalize(item) for item in data]

    return data
