"""Tests for JSON comparison functionality."""

from __future__ import annotations

from jsonify.core.diff import (
    DiffType,
    JsonDiff,
    compare_json,
)


def test_identical_objects_have_no_differences() -> None:
    old = {
        "name": "Alice",
        "age": 25,
    }

    new = {
        "name": "Alice",
        "age": 25,
    }

    assert compare_json(old, new) == []


def test_changed_value() -> None:
    old = {
        "status": "active",
    }

    new = {
        "status": "inactive",
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.CHANGED,
            path="$.status",
            old_value="active",
            new_value="inactive",
        )
    ]


def test_added_property() -> None:
    old = {
        "name": "Alice",
    }

    new = {
        "name": "Alice",
        "role": "admin",
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.ADDED,
            path="$.role",
            new_value="admin",
        )
    ]


def test_removed_property() -> None:
    old = {
        "name": "Alice",
        "age": 25,
    }

    new = {
        "name": "Alice",
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.REMOVED,
            path="$.age",
            old_value=25,
        )
    ]


def test_nested_change() -> None:
    old = {
        "user": {
            "profile": {
                "name": "Alice",
            }
        }
    }

    new = {
        "user": {
            "profile": {
                "name": "Bob",
            }
        }
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.CHANGED,
            path="$.user.profile.name",
            old_value="Alice",
            new_value="Bob",
        )
    ]


def test_array_value_change() -> None:
    old = {
        "users": [
            "Alice",
            "Bob",
        ]
    }

    new = {
        "users": [
            "Alice",
            "Charlie",
        ]
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.CHANGED,
            path="$.users[1]",
            old_value="Bob",
            new_value="Charlie",
        )
    ]


def test_array_item_added() -> None:
    old = {
        "users": [
            "Alice",
        ]
    }

    new = {
        "users": [
            "Alice",
            "Bob",
        ]
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.ADDED,
            path="$.users[1]",
            new_value="Bob",
        )
    ]


def test_array_item_removed() -> None:
    old = {
        "users": [
            "Alice",
            "Bob",
        ]
    }

    new = {
        "users": [
            "Alice",
        ]
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.REMOVED,
            path="$.users[1]",
            old_value="Bob",
        )
    ]


def test_type_change() -> None:
    old = {
        "age": 25,
    }

    new = {
        "age": "25",
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.TYPE_CHANGED,
            path="$.age",
            old_value=25,
            new_value="25",
        )
    ]


def test_boolean_and_integer_are_different_types() -> None:
    old = {
        "value": True,
    }

    new = {
        "value": 1,
    }

    result = compare_json(old, new)

    assert result == [
        JsonDiff(
            diff_type=DiffType.TYPE_CHANGED,
            path="$.value",
            old_value=True,
            new_value=1,
        )
    ]


def test_special_character_key_uses_bracket_path() -> None:
    old = {
        "first name": "Alice",
    }

    new = {
        "first name": "Bob",
    }

    result = compare_json(old, new)

    assert result[0].path == '$["first name"]'


def test_multiple_differences() -> None:
    old = {
        "name": "Alice",
        "age": 25,
        "status": "active",
    }

    new = {
        "name": "Alice",
        "status": "inactive",
        "role": "admin",
    }

    result = compare_json(old, new)

    assert len(result) == 3

    assert any(
        difference.diff_type == DiffType.REMOVED
        and difference.path == "$.age"
        for difference in result
    )

    assert any(
        difference.diff_type == DiffType.ADDED
        and difference.path == "$.role"
        for difference in result
    )

    assert any(
        difference.diff_type == DiffType.CHANGED
        and difference.path == "$.status"
        for difference in result
    )