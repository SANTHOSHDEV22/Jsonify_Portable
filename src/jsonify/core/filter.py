"""Advanced JSON filtering that preserves the surrounding hierarchy.

Unlike the drill-down "Filtered View" (which narrows to one selected
path), this keeps the full tree shape but prunes it down to only the
branches that lead to a matching key/value/type — so a match ten levels
deep is still shown with all of its ancestor objects/arrays intact.
"""

from __future__ import annotations

from dataclasses import dataclass

from jsonify.core.models import JSONValue

_TYPE_NAMES = {
    type(None): "null",
    bool: "boolean",
    dict: "object",
    list: "array",
    str: "string",
    int: "number",
    float: "number",
}


def _type_name(value: JSONValue) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


@dataclass(slots=True)
class FilterCriteria:
    """What to keep when filtering a JSON document."""

    key_contains: str = ""
    value_contains: str = ""
    type_name: str = ""  # "", "object", "array", "string", "number", "boolean", "null"
    case_sensitive: bool = False

    def is_empty(self) -> bool:
        return not (self.key_contains or self.value_contains or self.type_name)


def filter_json(data: JSONValue, criteria: FilterCriteria) -> JSONValue | None:
    """
    Return a pruned copy of ``data`` containing only branches that lead to
    a node matching ``criteria``, or ``None`` if nothing matches.
    """

    if criteria.is_empty():
        return data

    matched, pruned = _filter_node(data, key=None, criteria=criteria)
    return pruned if matched else None


def _matches(key: str | None, value: JSONValue, criteria: FilterCriteria) -> bool:
    if criteria.type_name and _type_name(value) != criteria.type_name:
        return False

    if criteria.key_contains:
        haystack = key or ""
        needle = criteria.key_contains
        if not criteria.case_sensitive:
            haystack, needle = haystack.lower(), needle.lower()
        if needle not in haystack:
            return False

    if criteria.value_contains and not isinstance(value, dict | list):
        haystack = "" if value is None else str(value)
        needle = criteria.value_contains
        if not criteria.case_sensitive:
            haystack, needle = haystack.lower(), needle.lower()
        if needle not in haystack:
            return False
    elif criteria.value_contains and isinstance(value, dict | list):
        return False

    return True


def _filter_node(
    data: JSONValue,
    *,
    key: str | None,
    criteria: FilterCriteria,
) -> tuple[bool, JSONValue]:
    """Return (matched_or_has_matching_descendant, pruned_subtree)."""

    self_matches = _matches(key, data, criteria)

    if isinstance(data, dict):
        pruned: dict[str, JSONValue] = {}
        any_child_matches = False

        for child_key, child_value in data.items():
            child_matched, child_pruned = _filter_node(
                child_value, key=child_key, criteria=criteria
            )
            if child_matched:
                pruned[child_key] = child_pruned
                any_child_matches = True

        if self_matches:
            return True, data
        if any_child_matches:
            return True, pruned
        return False, None

    if isinstance(data, list):
        pruned_items: list[JSONValue] = []
        any_child_matches = False

        for item in data:
            child_matched, child_pruned = _filter_node(item, key=None, criteria=criteria)
            if child_matched:
                pruned_items.append(child_pruned)
                any_child_matches = True

        if self_matches:
            return True, data
        if any_child_matches:
            return True, pruned_items
        return False, None

    return self_matches, data
