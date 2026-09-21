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


def find_duplicate_keys(raw_text: str) -> list[str]:
    """
    Detect object keys that repeat within the same JSON object.

    Standard ``json.loads`` silently keeps only the last value for a
    duplicate key, so this is the only way to surface the mistake to the
    user. Returns a human-readable message per duplicated key found
    (an object can produce more than one message if several of its keys
    repeat, and the same key name can appear in multiple messages if it
    repeats in more than one object).

    Args:
        raw_text: The raw JSON text to check.

    Returns:
        A list of messages describing each duplicate-key occurrence.
        Empty if the text has no duplicate keys (or isn't valid JSON).
    """
    messages: list[str] = []

    def hook(pairs: list[tuple[str, JSONValue]]) -> dict[str, JSONValue]:
        counts: dict[str, int] = {}
        for key, _value in pairs:
            counts[key] = counts.get(key, 0) + 1

        for key, count in counts.items():
            if count > 1:
                messages.append(f'Key "{key}" appears {count} times in the same object.')

        return dict(pairs)

    try:
        json.loads(raw_text, object_pairs_hook=hook)
    except json.JSONDecodeError:
        pass

    return messages
