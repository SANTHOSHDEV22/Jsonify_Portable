"""Core JSON comparison functionality."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

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
    *,
    array_identity_key: str | None = None,
) -> list[JsonDiff]:
    """
    Compare two JSON values recursively.

    Args:
        old:
            Original JSON value.

        new:
            New JSON value.

        array_identity_key:
            When set, arrays of objects are matched by this key's value
            (e.g. ``"id"``) instead of by position — an item that moved
            from index 2 to index 0 is no longer reported as two
            unrelated changes. Arrays whose items aren't all objects
            containing this key fall back to positional comparison.

    Returns:
        All differences between the two values.
    """

    differences: list[JsonDiff] = []

    _compare_values(
        old=old,
        new=new,
        path="$",
        differences=differences,
        array_identity_key=array_identity_key,
    )

    return differences


def _compare_values(
    old: JSONValue,
    new: JSONValue,
    path: str,
    differences: list[JsonDiff],
    array_identity_key: str | None = None,
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
            array_identity_key=array_identity_key,
        )
        return

    if isinstance(old, list) and isinstance(new, list):
        _compare_arrays(
            old=old,
            new=new,
            path=path,
            differences=differences,
            array_identity_key=array_identity_key,
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
    array_identity_key: str | None = None,
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
            array_identity_key=array_identity_key,
        )


def _compare_arrays(
    old: list[JSONValue],
    new: list[JSONValue],
    path: str,
    differences: list[JsonDiff],
    array_identity_key: str | None = None,
) -> None:
    """Compare two JSON arrays, by identity key if usable, else by index."""

    if (
        array_identity_key
        and _all_have_identity(old, array_identity_key)
        and _all_have_identity(new, array_identity_key)
    ):
        _compare_arrays_by_identity(
            old=old,
            new=new,
            path=path,
            differences=differences,
            key=array_identity_key,
        )
        return

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
            array_identity_key=array_identity_key,
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


def _all_have_identity(items: list[JSONValue], key: str) -> bool:
    """Return whether every item is an object containing ``key``."""

    return bool(items) and all(isinstance(item, dict) and key in item for item in items)


def _index_by_identity(items: list[JSONValue], key: str) -> dict[Any, dict[str, JSONValue]]:
    """Map identity value -> item, for items already known to be objects."""

    return {item[key]: item for item in items if isinstance(item, dict)}


def _compare_arrays_by_identity(
    old: list[JSONValue],
    new: list[JSONValue],
    path: str,
    differences: list[JsonDiff],
    key: str,
) -> None:
    """Compare two arrays of objects, matching items by identity value."""

    old_by_id = _index_by_identity(old, key)
    new_by_id = _index_by_identity(new, key)

    old_ids = set(old_by_id)
    new_ids = set(new_by_id)

    for identity in sorted(old_ids - new_ids, key=str):
        differences.append(
            JsonDiff(
                diff_type=DiffType.REMOVED,
                path=f"{path}[{key}={identity!r}]",
                old_value=old_by_id[identity],
            )
        )

    for identity in sorted(new_ids - old_ids, key=str):
        differences.append(
            JsonDiff(
                diff_type=DiffType.ADDED,
                path=f"{path}[{key}={identity!r}]",
                new_value=new_by_id[identity],
            )
        )

    for identity in sorted(old_ids & new_ids, key=str):
        _compare_values(
            old=old_by_id[identity],
            new=new_by_id[identity],
            path=f"{path}[{key}={identity!r}]",
            differences=differences,
            array_identity_key=key,
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

    escaped_key = key.replace("\\", "\\\\").replace('"', '\\"')

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
