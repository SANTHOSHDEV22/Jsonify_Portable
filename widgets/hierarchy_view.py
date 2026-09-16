"""
widgets/hierarchy_view.py
---------------------------
Renders a JSON payload as an indented, ASCII-art hierarchy outline —
a plain-text alternative to the interactive Tree View, handy for
scanning a deep structure at a glance or copy/pasting elsewhere.

Example output:
    └── root {3}
        ├── company: "Acme Manufacturing"
        ├── location {2}
        │   ├── city: "Chennai"
        │   └── country: "India"
        └── production_lines [2]
            ├── [0] {4}
            │   ├── id: "PL-01"
            │   └── ...
            └── [1] {4}
"""
from __future__ import annotations

import json
from typing import Any, List


def build_hierarchy_text(data: Any) -> str:
    """Render `data` as an indented Unicode box-drawing outline.

    Args:
        data: Any JSON-compatible Python value (parsed payload).

    Returns:
        A multi-line string ready to drop into a read-only text widget.
    """
    lines: List[str] = []
    _walk(data, "root", prefix="", is_last=True, lines=lines)
    return "\n".join(lines)


def _walk(data: Any, label: str, prefix: str, is_last: bool, lines: List[str]) -> None:
    connector = "└── " if is_last else "├── "

    if isinstance(data, dict):
        lines.append(f"{prefix}{connector}{label} {{{len(data)}}}")
        next_prefix = prefix + ("    " if is_last else "│   ")
        items = list(data.items())
        for index, (key, value) in enumerate(items):
            _walk(value, str(key), next_prefix, index == len(items) - 1, lines)

    elif isinstance(data, list):
        lines.append(f"{prefix}{connector}{label} [{len(data)}]")
        next_prefix = prefix + ("    " if is_last else "│   ")
        for index, item in enumerate(data):
            _walk(item, f"[{index}]", next_prefix, index == len(data) - 1, lines)

    else:
        lines.append(f"{prefix}{connector}{label}: {json.dumps(data)}")


def _contains_key(data: Any, target_key: str) -> bool:
    """True if `target_key` appears anywhere in `data`, at any depth."""
    if isinstance(data, dict):
        return any(k == target_key or _contains_key(v, target_key) for k, v in data.items())
    if isinstance(data, list):
        return any(_contains_key(item, target_key) for item in data)
    return False


def build_filtered_hierarchy_text(data: Any, target_key: str) -> str:
    """Render the same box-drawing tree as `build_hierarchy_text`, but
    pruned to only the branches that lead to an occurrence of
    `target_key` — every sibling key/item that doesn't contain a match
    is left out entirely, rather than shown empty.

    A key that matches `target_key` is always shown with its full value
    (even if that value is itself a nested object/array) — only the
    *path down to* a match is pruned, not the match's own contents.

    Args:
        data: Any JSON-compatible Python value (parsed payload).
        target_key: The key name to keep in the tree.

    Returns:
        A multi-line string, or a one-line "no matches" message if
        `target_key` doesn't appear anywhere in `data`.

    Example:
        >>> build_filtered_hierarchy_text(
        ...     [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}], "id"
        ... )
        '└── root [2]\\n    ├── [0] {1}\\n    │   └── id: 1\\n    └── [1] {1}\\n        └── id: 2'
    """
    lines: List[str] = []
    _walk_filtered(data, "root", prefix="", is_last=True, lines=lines, target_key=target_key)
    if not lines:
        return f"No occurrences of key '{target_key}' found."
    return "\n".join(lines)


def _walk_filtered(
    data: Any, label: str, prefix: str, is_last: bool, lines: List[str], target_key: str
) -> None:
    if isinstance(data, dict):
        # Keep only entries that are themselves a match, or that contain
        # a match somewhere further down — drop everything else.
        relevant = []
        for key, value in data.items():
            if key == target_key:
                relevant.append((key, value, True))
            elif _contains_key(value, target_key):
                relevant.append((key, value, False))
        if not relevant:
            return

        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{label} {{{len(relevant)}}}")
        next_prefix = prefix + ("    " if is_last else "│   ")

        for index, (key, value, is_hit) in enumerate(relevant):
            last_child = index == len(relevant) - 1
            if is_hit:
                # A direct match: show it (and its full value) exactly
                # like the unfiltered tree would, no further pruning.
                _walk(value, str(key), next_prefix, last_child, lines)
            else:
                _walk_filtered(value, str(key), next_prefix, last_child, lines, target_key)

    elif isinstance(data, list):
        relevant_items = [(index, item) for index, item in enumerate(data) if _contains_key(item, target_key)]
        if not relevant_items:
            return

        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{label} [{len(relevant_items)}]")
        next_prefix = prefix + ("    " if is_last else "│   ")

        for position, (original_index, item) in enumerate(relevant_items):
            last_child = position == len(relevant_items) - 1
            _walk_filtered(item, f"[{original_index}]", next_prefix, last_child, lines, target_key)

    # Scalars can't contain a nested key, so a scalar only ever appears
    # here via the is_hit branch above (handled by the caller).


def _collect_targets(data: Any, key_path: List[str]) -> List[Any]:
    """Follow `key_path` from `data`, level by level, transparently
    stepping into list items along the way, and return every value
    reached at the end (there can be several — one per matching branch,
    e.g. one per payload in a multi-payload array).

    An empty `key_path` means "the dicts at this level" — if `data` is
    itself a list, that's each of its dict items (flattened); if it's a
    dict, that's just `data` itself.
    """
    if not key_path:
        if isinstance(data, list):
            result: List[Any] = []
            for item in data:
                result.extend(_collect_targets(item, []))
            return result
        return [data]

    if isinstance(data, list):
        result = []
        for item in data:
            result.extend(_collect_targets(item, key_path))
        return result

    if isinstance(data, dict):
        target = key_path[0]
        if target not in data:
            return []
        return _collect_targets(data[target], key_path[1:])

    return []  # scalar, but path remains: dead end


def keys_at_path(data: Any, key_path: List[str]) -> List[str]:
    """List the keys available one level below `key_path`, across every
    branch that reaches that far — this is what populates each level's
    dropdown in the Filtered View tab.

    Args:
        data: Any JSON-compatible Python value (parsed payload).
        key_path: Keys already chosen in levels above this one, in
            order. An empty list means "top-level keys".

    Returns:
        A sorted list of every distinct key found in the dict(s) at
        that position. Empty if nothing is reachable there (e.g. the
        path leads only to scalars, or doesn't exist at all).

    Example:
        >>> payload = [{"a": {"b": 1}}, {"a": {"c": 2}}]
        >>> keys_at_path(payload, [])
        ['a']
        >>> keys_at_path(payload, ["a"])
        ['b', 'c']
    """
    keys = set()
    for target in _collect_targets(data, key_path):
        if isinstance(target, dict):
            keys.update(target.keys())
    return sorted(keys)


def _has_path(data: Any, key_path: List[str]) -> bool:
    """Whether descending through `key_path` from `data` reaches
    anything at all (following into list items transparently)."""
    if not key_path:
        return True
    if isinstance(data, dict):
        target = key_path[0]
        return target in data and _has_path(data[target], key_path[1:])
    if isinstance(data, list):
        return any(_has_path(item, key_path) for item in data)
    return False  # scalar, but path remains: dead end


def build_path_filtered_hierarchy_text(data: Any, key_path: List[str]) -> str:
    """Render the payload pruned to one explicit, ordered chain of keys
    — e.g. `["departments", "teams"]` follows exactly that route
    through every payload/array item along the way, then shows
    everything under the final key in full (unpruned) once the chosen
    path is fully matched.

    This is what the "Show" button in the Filtered View tab calls,
    using the keys currently selected across all of its level dropdowns.

    Args:
        data: Any JSON-compatible Python value (parsed payload).
        key_path: The ordered list of keys chosen, one per level
            (e.g. `["departments", "teams", "members"]`).

    Returns:
        A multi-line string in the same box-drawing style as
        `build_hierarchy_text`, or a one-line message if nothing
        matches or `key_path` is empty.

    Example:
        >>> build_path_filtered_hierarchy_text(
        ...     [{"a": {"b": 1}}, {"a": {"b": 2}}], ["a", "b"]
        ... )
        '└── root [2]\\n    ├── [0] {1}\\n    │   └── a {1}\\n    │       └── b: 1\\n    └── [1] {1}\\n        └── a {1}\\n            └── b: 2'
    """
    if not key_path:
        return "Select at least one level above, then click Show."

    lines: List[str] = []
    _walk_path(data, "root", prefix="", is_last=True, lines=lines, key_path=key_path, depth=0)
    if not lines:
        return "No matches found for: " + " → ".join(key_path)
    return "\n".join(lines)


def _walk_path(
    data: Any, label: str, prefix: str, is_last: bool, lines: List[str], key_path: List[str], depth: int
) -> None:
    # The chosen path has been fully matched — show everything from here
    # on exactly like the unfiltered tree would, no more pruning.
    if depth >= len(key_path):
        _walk(data, label, prefix, is_last, lines)
        return

    remaining = key_path[depth:]
    if not _has_path(data, remaining):
        return

    if isinstance(data, list):
        # List items are transparent with respect to the path: they
        # don't consume a path segment themselves, only their own dict
        # keys do — so `depth` is passed through unchanged.
        relevant = [(index, item) for index, item in enumerate(data) if _has_path(item, remaining)]
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{label} [{len(relevant)}]")
        next_prefix = prefix + ("    " if is_last else "│   ")
        for position, (original_index, item) in enumerate(relevant):
            last_child = position == len(relevant) - 1
            _walk_path(item, f"[{original_index}]", next_prefix, last_child, lines, key_path, depth)
        return

    if isinstance(data, dict):
        target = key_path[depth]
        value = data[target]  # present: _has_path above already confirmed it
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{label} {{1}}")
        next_prefix = prefix + ("    " if is_last else "│   ")
        _walk_path(value, target, next_prefix, True, lines, key_path, depth + 1)
        return

    # Scalar with path remaining: _has_path would already have been
    # False for this branch, so this point is unreachable in practice.