"""JSON traversal, search, and statistics utilities."""

from __future__ import annotations

from jsonify.core.models import JSONPathMatch, JSONValue


def extract_unique_keys(data: JSONValue) -> list[str]:
    """
    Extract all unique object keys from a JSON structure.

    Args:
        data: Parsed JSON data.

    Returns:
        A sorted list of unique keys.
    """
    keys: set[str] = set()

    def walk(node: JSONValue) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                keys.add(key)
                walk(value)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)

    return sorted(keys)


def find_values_by_key(
    data: JSONValue,
    target_key: str,
    path: str = "$",
) -> list[JSONPathMatch]:
    """
    Find all values associated with a specific key.

    Args:
        data: Parsed JSON data.
        target_key: Key to search for.
        path: Current JSON path used during recursion.

    Returns:
        A list of path-value matches.
    """
    matches: list[JSONPathMatch] = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}"

            if key == target_key:
                matches.append((current_path, value))

            matches.extend(
                find_values_by_key(
                    value,
                    target_key,
                    current_path,
                )
            )

    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path = f"{path}[{index}]"

            matches.extend(
                find_values_by_key(
                    item,
                    target_key,
                    current_path,
                )
            )

    return matches


def calculate_json_stats(data: JSONValue) -> dict[str, int]:
    """
    Calculate structural statistics for JSON data.

    The JSON tree is traversed only once for efficiency.

    Args:
        data: Parsed JSON data.

    Returns:
        Statistics containing object/array/leaf counts, maximum depth,
        unique key count, and a breakdown of leaf values by type
        (nulls, booleans, strings, and numbers).
    """
    stats = {
        "objects": 0,
        "arrays": 0,
        "leaves": 0,
        "max_depth": 0,
        "keys": 0,
        "nulls": 0,
        "booleans": 0,
        "strings": 0,
        "numbers": 0,
    }

    unique_keys: set[str] = set()

    def walk(node: JSONValue, depth: int = 0) -> None:
        stats["max_depth"] = max(
            stats["max_depth"],
            depth,
        )

        if isinstance(node, dict):
            stats["objects"] += 1

            for key, value in node.items():
                unique_keys.add(key)
                walk(value, depth + 1)

        elif isinstance(node, list):
            stats["arrays"] += 1

            for item in node:
                walk(item, depth + 1)

        else:
            stats["leaves"] += 1

            if node is None:
                stats["nulls"] += 1
            elif isinstance(node, bool):
                stats["booleans"] += 1
            elif isinstance(node, str):
                stats["strings"] += 1
            elif isinstance(node, int | float):
                stats["numbers"] += 1

    walk(data)

    stats["keys"] = len(unique_keys)

    return stats


def to_table_rows(
    data: JSONValue,
) -> tuple[list[str], list[list[JSONValue]]]:
    """
    Flatten an array of objects into table columns and rows.

    Column order follows first-seen key order across all rows. Rows that
    are missing a column get ``None`` for that cell; rows that aren't
    objects at all are skipped.

    Args:
        data: A JSON array, ideally of objects.

    Returns:
        A tuple of (column names, row values) suitable for a table widget.
    """
    if not isinstance(data, list):
        return [], []

    columns: list[str] = []
    seen_columns: set[str] = set()

    for item in data:
        if not isinstance(item, dict):
            continue
        for key in item:
            if key not in seen_columns:
                seen_columns.add(key)
                columns.append(key)

    rows: list[list[JSONValue]] = [
        [item.get(column) for column in columns] for item in data if isinstance(item, dict)
    ]

    return columns, rows
