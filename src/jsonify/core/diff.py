"""Core JSON comparison functionality."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from jsonify.core.models import JSONValue


class DiffType(StrEnum):
    """Type of difference found between two JSON values."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    TYPE_CHANGED = "type_changed"


@dataclass(frozen=True, slots=True)
class JsonDiff:
    """Represents one difference between two JSON documents."""

    diff_type: DiffType
    path: str
    old_value: JSONValue = None
    new_value: JSONValue = None

    @property
    def symbol(self) -> str:
        """Return a short symbol representing the difference."""

        return {
            DiffType.ADDED: "+",
            DiffType.REMOVED: "-",
            DiffType.CHANGED: "~",
            DiffType.TYPE_CHANGED: "!",
        }[self.diff_type]


def compare_json(
    old: JSONValue,
    new: JSONValue,
) -> list[JsonDiff]:
    """
    Compare two JSON values recursively.

    Args:
        old:
            Original JSON value.

        new:
            New JSON value.

    Returns:
        All differences between the two values.
    """

    differences: list[JsonDiff] = []

    _compare_values(
        old=old,
        new=new,
        path="$",
        differences=differences,
    )

    return differences


def _compare_values(
    old: JSONValue,
    new: JSONValue,
    path: str,
    differences: list[JsonDiff],
) -> None:
    """Recursively compare two JSON values."""

    if _json_type(old) != _json_type(new):
        differences.append(
            JsonDiff(
                diff_type=DiffType.TYPE_CHANGED,
                path=path,
                old_value=old,
                new_value=new,
            )
        )
        return

    if isinstance(old, dict) and isinstance(new, dict):
        _compare_objects(
            old=old,
            new=new,
            path=path,
            differences=differences,
        )
        return

    if isinstance(old, list) and isinstance(new, list):
        _compare_arrays(
            old=old,
            new=new,
            path=path,
            differences=differences,
        )
        return

    if old != new:
        differences.append(
            JsonDiff(
                diff_type=DiffType.CHANGED,
                path=path,
                old_value=old,
                new_value=new,
            )
        )


def _compare_objects(
    old: dict[str, JSONValue],
    new: dict[str, JSONValue],
    path: str,
    differences: list[JsonDiff],
) -> None:
    """Compare two JSON objects."""

    old_keys = set(old)
    new_keys = set(new)

    removed_keys = old_keys - new_keys
    added_keys = new_keys - old_keys
    common_keys = old_keys & new_keys

    for key in sorted(removed_keys, key=str.casefold):
        differences.append(
            JsonDiff(
                diff_type=DiffType.REMOVED,
                path=_object_path(path, key),
                old_value=old[key],
            )
        )

    for key in sorted(added_keys, key=str.casefold):
        differences.append(
            JsonDiff(
                diff_type=DiffType.ADDED,
                path=_object_path(path, key),
                new_value=new[key],
            )
        )

    for key in sorted(common_keys, key=str.casefold):
        _compare_values(
            old=old[key],
            new=new[key],
            path=_object_path(path, key),
            differences=differences,
        )


def _compare_arrays(
    old: list[JSONValue],
    new: list[JSONValue],
    path: str,
    differences: list[JsonDiff],
) -> None:
    """Compare two JSON arrays by index."""

    common_length = min(
        len(old),
        len(new),
    )

    for index in range(common_length):
        _compare_values(
            old=old[index],
            new=new[index],
            path=f"{path}[{index}]",
            differences=differences,
        )

    for index in range(common_length, len(old)):
        differences.append(
            JsonDiff(
                diff_type=DiffType.REMOVED,
                path=f"{path}[{index}]",
                old_value=old[index],
            )
        )

    for index in range(common_length, len(new)):
        differences.append(
            JsonDiff(
                diff_type=DiffType.ADDED,
                path=f"{path}[{index}]",
                new_value=new[index],
            )
        )


def _object_path(
    parent: str,
    key: str,
) -> str:
    """
    Create a readable JSON path.

    Simple keys use dot notation:

        $.user.name

    Keys containing special characters use bracket notation:

        $["first name"]
    """

    if key.isidentifier():
        return f"{parent}.{key}"

    escaped_key = (
        key.replace("\\", "\\\\")
        .replace('"', '\\"')
    )

    return f'{parent}["{escaped_key}"]'


def _json_type(value: JSONValue) -> str:
    """
    Return the logical JSON type.

    bool is checked before int because bool is a subclass
    of int in Python.
    """

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

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "number"

    return type(value).__name__