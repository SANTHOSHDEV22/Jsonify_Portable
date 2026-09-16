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
        Statistics containing object count, array count,
        leaf count, maximum depth, and unique key count.
    """
    stats = {
        "objects": 0,
        "arrays": 0,
        "leaves": 0,
        "max_depth": 0,
        "keys": 0,
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

    walk(data)

    stats["keys"] = len(unique_keys)

    return stats