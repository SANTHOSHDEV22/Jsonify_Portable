"""Hierarchy-view rendering and filtering for JSON payloads."""

from __future__ import annotations

import json

from jsonify.core.models import JSONValue

def build_hierarchy_text(
    data: JSONValue,
) -> str:
    """
    Convert a JSON payload into readable hierarchy text, using
    box-drawing tree connectors (├──, └──, │) to show parent/child
    relationships at a glance.

    Args:
        data:
            Parsed JSON payload.

    Returns:
        Formatted hierarchy representation.
    """
    lines: list[str] = []

    _append_hierarchy(
        value=data,
        lines=lines,
        prefix="",
        is_last=True,
        label="$",
    )

    return "\n".join(lines)


def _append_hierarchy(
    value: JSONValue,
    lines: list[str],
    prefix: str,
    is_last: bool,
    label: str,
) -> None:
    """Recursively append box-drawing hierarchy lines.

    `prefix` accumulates the vertical connector columns ("│   ") of
    every ancestor that still has more siblings below it, so lines
    stay connected all the way down the tree rather than just being
    flatly indented.
    """

    connector = "└── " if is_last else "├── "

    if isinstance(value, dict):
        lines.append(f"{prefix}{connector}{label} {{{len(value)}}}")

        next_prefix = prefix + ("    " if is_last else "│   ")
        items = list(value.items())

        for index, (key, child_value) in enumerate(items):
            _append_hierarchy(
                value=child_value,
                lines=lines,
                prefix=next_prefix,
                is_last=index == len(items) - 1,
                label=str(key),
            )

        return

    if isinstance(value, list):
        lines.append(f"{prefix}{connector}{label} [{len(value)}]")

        next_prefix = prefix + ("    " if is_last else "│   ")

        for index, child_value in enumerate(value):
            _append_hierarchy(
                value=child_value,
                lines=lines,
                prefix=next_prefix,
                is_last=index == len(value) - 1,
                label=f"[{index}]",
            )

        return

    lines.append(f"{prefix}{connector}{label}: {_format_primitive(value)}")


def _format_primitive(
    value: JSONValue,
) -> str:
    """Format a primitive JSON value."""

    if isinstance(value, str):
        return json.dumps(
            value,
            ensure_ascii=False,
        )

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


def keys_at_path(
    data: JSONValue,
    path: list[str],
) -> list[str]:
    """
    Return available object keys below a selected hierarchy path.

    Lists are traversed automatically so users can drill through
    arrays of objects without selecting numeric array indexes.

    Args:
        data:
            Parsed JSON payload.

        path:
            Previously selected object keys.

    Returns:
        Sorted list of keys available at the next level.
    """
    nodes: list[JSONValue] = [data]

    for key in path:
        next_nodes: list[JSONValue] = []

        for node in nodes:
            _collect_values_for_key(
                node=node,
                key=key,
                results=next_nodes,
            )

        nodes = next_nodes

        if not nodes:
            return []

    keys: set[str] = set()

    for node in nodes:
        _collect_immediate_keys(
            node=node,
            keys=keys,
        )

    return sorted(
        keys,
        key=str.casefold,
    )


def _collect_immediate_keys(
    node: JSONValue,
    keys: set[str],
) -> None:
    """Collect keys directly available at a hierarchy level."""

    if isinstance(node, dict):
        keys.update(node.keys())

        return

    if isinstance(node, list):
        for item in node:
            if isinstance(item, dict):
                keys.update(item.keys())


def _collect_values_for_key(
    node: JSONValue,
    key: str,
    results: list[JSONValue],
) -> None:
    """
    Collect values matching a key at the current logical level.

    Arrays are transparent for hierarchy navigation.
    """

    if isinstance(node, dict):
        if key in node:
            results.append(node[key])

        return

    if isinstance(node, list):
        for item in node:
            _collect_values_for_key(
                node=item,
                key=key,
                results=results,
            )


def build_path_filtered_hierarchy_text(
    data: JSONValue,
    path: list[str],
) -> str:
    """Build a hierarchy containing only the selected key path.

    Container nodes (objects and arrays) are kept so the result has the
    same visual shape as Hierarchy View, while sibling keys that were not
    selected are omitted.  This also works when arrays occur at any level
    of the selected path.
    """
    if not path:
        return build_hierarchy_text(data)

    found, filtered = _filter_to_path(
        value=data,
        path=path,
    )

    if not found:
        return "No values were found for path:\n\n" + " → ".join(path)

    return build_hierarchy_text(filtered)


def _filter_to_path(
    value: JSONValue,
    path: list[str],
) -> tuple[bool, JSONValue]:
    """Project ``value`` to ``path`` while preserving containers.

    Lists are transparent to the path: selecting ``short_item_number``
    from a root list keeps the list and each matching object, but removes
    every unselected key from those objects.
    """
    if isinstance(value, list):
        filtered_items: list[JSONValue] = []

        for item in value:
            found, filtered_item = _filter_to_path(
                value=item,
                path=path,
            )
            if found:
                filtered_items.append(filtered_item)

        return bool(filtered_items), filtered_items

    if not path or not isinstance(value, dict):
        return False, {}

    key = path[0]
    if key not in value:
        return False, {}

    child = value[key]

    if len(path) == 1:
        return True, {key: child}

    found, filtered_child = _filter_to_path(
        value=child,
        path=path[1:],
    )
    if not found:
        return False, {}

    return True, {key: filtered_child}
