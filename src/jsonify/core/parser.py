"""JSON parsing utilities for Jsonify."""

from __future__ import annotations

import json

from jsonify.core.models import JSONValue

_DECODER = json.JSONDecoder()
_SEPARATORS = frozenset(" \t\r\n,")


def parse_json(raw_text: str) -> JSONValue:
    """
    Parse a single JSON document.

    Raises:
        json.JSONDecodeError: If the input is not valid JSON.
    """
    return json.loads(raw_text)


def parse_multiple_json(raw_text: str) -> tuple[JSONValue, int]:
    """
    Parse one or more consecutive JSON documents.

    Supports input such as:
        {"id": 1}
        {"id": 2}

    Returns:
        A tuple containing:
        - The parsed JSON value.
        - The number of parsed documents.

    Raises:
        json.JSONDecodeError: If the input contains invalid JSON.
    """
    documents: list[JSONValue] = []
    index = 0

    while index < len(raw_text):
        # Skip whitespace and separators between documents.
        while index < len(raw_text) and raw_text[index] in _SEPARATORS:
            index += 1

        if index >= len(raw_text):
            break

        value, index = _DECODER.raw_decode(raw_text, index)

        if isinstance(value, list):
            documents.extend(value)
        else:
            documents.append(value)

    # Preserve JSONDecodeError behavior for empty/invalid input.
    if not documents:
        json.loads(raw_text)

    result: JSONValue = documents[0] if len(documents) == 1 else documents

    return result, len(documents)
