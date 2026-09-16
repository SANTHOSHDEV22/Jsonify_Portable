"""
json_utils.py
-------------
Pure, framework-independent helpers for working with an arbitrary JSON
payload: parsing, collecting every unique key, and finding all values
that live under a given key (wherever it appears, however deeply nested).

No Qt / UI dependency here on purpose, so this can be unit-tested or
reused outside the desktop app.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple, Union

JSONType = Union[dict, list, str, int, float, bool, None]


def parse_json(raw_text: str) -> JSONType:
    """Parse a raw JSON string into a Python object.

    Args:
        raw_text: The JSON document as a string.

    Returns:
        The parsed Python object (dict, list, or scalar).

    Raises:
        json.JSONDecodeError: if `raw_text` is not valid JSON.

    Example:
        >>> parse_json('{"a": 1, "b": [1, 2, 3]}')
        {'a': 1, 'b': [1, 2, 3]}
    """
    return json.loads(raw_text)


_multi_decoder = json.JSONDecoder()
_SKIPPABLE = " \t\r\n,"


def parse_multi_json(raw_text: str) -> Tuple[JSONType, int]:
    """Parse one or more JSON documents/values pasted together in `raw_text`.

    A plain `json.loads()` only accepts exactly one JSON document, and
    rejects anything extra after it. This is deliberately permissive
    about how several documents are glued together, since people paste
    sample payloads in all sorts of shapes:

        {"a": 1}{"b": 2}            <- back-to-back, no separator
        {"a": 1}\\n{"b": 2}          <- separated by whitespace/newlines
        {"a": 1}, {"b": 2}          <- separated by a stray comma
        [{"a": 1}, {"b": 2}]        <- already a single JSON array
        [{"a": 1}],{"b": 2},{"c":3} <- a mix of all of the above

    It reads one complete JSON value at a time (skipping over any
    whitespace and/or commas in between — commas are never valid
    between two independent top-level JSON documents, so treating one
    as a separator here is unambiguous), and if a value it just read is
    itself a JSON array, that array's own items are folded in
    individually rather than kept as one nested list — so an array of
    payloads and several standalone payloads all end up in the same
    flat collection.

    Args:
        raw_text: One or more JSON documents, in any of the shapes above.

    Returns:
        A (value, doc_count) tuple:
        - If exactly one item was found overall, `value` is that item
          as-is (a dict/list/scalar) — same as `parse_json`.
        - If more than one was found, `value` is a list containing all
          of them in order, so every existing view (tree/hierarchy/
          graph/key-filter) just treats it as one JSON array — no
          special-casing needed downstream.
        `doc_count` is how many items ended up in the flat collection,
        for UI feedback (e.g. "Loaded 3 payloads").

    Raises:
        json.JSONDecodeError: if no valid JSON value is found at all.

    Example:
        >>> parse_multi_json('{"a": 1}')
        ({'a': 1}, 1)
        >>> parse_multi_json('{"a": 1}\\n{"b": 2}')
        ([{'a': 1}, {'b': 2}], 2)
        >>> parse_multi_json('[{"a": 1}, {"b": 2}], {"c": 3}')
        ([{'a': 1}, {'b': 2}, {'c': 3}], 3)
    """
    index = 0
    length = len(raw_text)
    documents: List[JSONType] = []

    while index < length:
        while index < length and raw_text[index] in _SKIPPABLE:
            index += 1
        if index >= length:
            break

        value, end_index = _multi_decoder.raw_decode(raw_text, index)
        if isinstance(value, list):
            documents.extend(value)
        else:
            documents.append(value)
        index = end_index

    if not documents:
        # Reuse json.loads' own error for an empty/whitespace-only input,
        # so the caller gets a normal, familiar JSONDecodeError.
        json.loads(raw_text)

    if len(documents) == 1:
        return documents[0], 1
    return documents, len(documents)


def extract_unique_keys(data: JSONType, keys: Optional[Set[str]] = None) -> List[str]:
    """Recursively walk a JSON structure and collect every unique key name.

    Works through nested dicts and lists of any depth. Keys are
    deduplicated and returned sorted alphabetically — this is what
    populates the key dropdown in the control bar.

    Args:
        data: Any JSON-compatible Python value.
        keys: Internal accumulator (do not pass this in manually).

    Returns:
        A sorted list of every distinct key found anywhere in `data`.

    Example:
        >>> extract_unique_keys({"a": 1, "b": {"c": 2, "a": 3}})
        ['a', 'b', 'c']
    """
    if keys is None:
        keys = set()

    if isinstance(data, dict):
        for key, value in data.items():
            keys.add(key)
            extract_unique_keys(value, keys)
    elif isinstance(data, list):
        for item in data:
            extract_unique_keys(item, keys)

    return sorted(keys)


def find_values_by_key(
    data: JSONType, target_key: str, path: str = "$"
) -> List[Tuple[str, JSONType]]:
    """Recursively find every occurrence of `target_key` in a JSON structure.

    This powers "select a key in the dropdown -> show its data".
    Because the same key can appear multiple times at different places
    in a payload (e.g. "id" under both "user" and "order"), this
    returns every match paired with a JSONPath-like string showing
    exactly where it came from.

    Args:
        data: Any JSON-compatible Python value.
        target_key: The key name to search for.
        path: Internal accumulator for the current JSONPath (do not pass
            this in manually).

    Returns:
        A list of (json_path, value) tuples, one per match, in the
        order they were encountered.

    Example:
        >>> payload = {"user": {"id": 1}, "items": [{"id": 2}, {"id": 3}]}
        >>> find_values_by_key(payload, "id")
        [('$.user.id', 1), ('$.items[0].id', 2), ('$.items[1].id', 3)]
    """
    matches: List[Tuple[str, JSONType]] = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}"
            if key == target_key:
                matches.append((new_path, value))
            matches.extend(find_values_by_key(value, target_key, new_path))
    elif isinstance(data, list):
        for index, item in enumerate(data):
            new_path = f"{path}[{index}]"
            matches.extend(find_values_by_key(item, target_key, new_path))

    return matches


def json_stats(data: JSONType) -> Dict[str, int]:
    """Compute quick summary stats about a JSON payload (keys/objects/etc).

    Example:
        >>> json_stats({"a": {"b": [1, 2]}})
        {'objects': 2, 'arrays': 1, 'leaves': 2, 'max_depth': 2, 'keys': 2}
    """
    stats = {"objects": 0, "arrays": 0, "leaves": 0, "max_depth": 0}

    def walk(node: JSONType, depth: int) -> None:
        stats["max_depth"] = max(stats["max_depth"], depth)
        if isinstance(node, dict):
            stats["objects"] += 1
            for value in node.values():
                walk(value, depth + 1)
        elif isinstance(node, list):
            stats["arrays"] += 1
            for item in node:
                walk(item, depth + 1)
        else:
            stats["leaves"] += 1

    walk(data, 0)
    stats["keys"] = len(extract_unique_keys(data))
    return stats