"""Hierarchy-view rendering and filtering for JSON payloads."""

from __future__ import annotations

import json

from jsonify.core.models import JSONValue

_INDENT = "    "


def build_hierarchy_text(
    data: JSONValue,
) -> str:
    """
    Convert a JSON payload into readable hierarchy text.

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
        depth=0,
        label="$",
    )

    return "\n".join(lines)


def _append_hierarchy(
    value: JSONValue,
    lines: list[str],
    depth: int,
    label: str,
) -> None:
    """Recursively append hierarchy lines."""

    indentation = _INDENT * depth

    if isinstance(value, dict):
        lines.append(f"{indentation}{label} {{")

        for key, child_value in value.items():
            _append_hierarchy(
                value=child_value,
                lines=lines,
                depth=depth + 1,
                label=str(key),
            )

        lines.append(f"{indentation}}}")

        return

    if isinstance(value, list):
        lines.append(f"{indentation}{label} [")

        for index, child_value in enumerate(value):
            _append_hierarchy(
                value=child_value,
                lines=lines,
                depth=depth + 1,
                label=f"[{index}]",
            )

        lines.append(f"{indentation}]")

        return

    lines.append(f"{indentation}{label}: {_format_primitive(value)}")


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
    """
    Build hierarchy text for values matching a selected key path.

    Args:
        data:
            Parsed JSON payload.

        path:
            Selected hierarchy keys.

    Returns:
        Formatted matching JSON hierarchy.
    """
    if not path:
        return build_hierarchy_text(data)

    matches = _resolve_path(
        data=data,
        path=path,
    )

    if not matches:
        return "No values were found for path:\n\n" + " → ".join(path)

    lines: list[str] = [
        f"Path: {' → '.join(path)}",
        f"Matches: {len(matches)}",
        "",
    ]

    for index, value in enumerate(
        matches,
        start=1,
    ):
        if len(matches) > 1:
            lines.append(f"--- Match {index} ---")

        lines.append(build_hierarchy_text(value))

        if index < len(matches):
            lines.append("")

    return "\n".join(lines)


def _resolve_path(
    data: JSONValue,
    path: list[str],
) -> list[JSONValue]:
    """Resolve all values matching a hierarchy key path."""

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
            break

    return nodes
