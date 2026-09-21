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
        difference.diff_type == DiffType.REMOVED and difference.path == "$.age"
        for difference in result
    )

    assert any(
        difference.diff_type == DiffType.ADDED and difference.path == "$.role"
        for difference in result
    )

    assert any(
        difference.diff_type == DiffType.CHANGED and difference.path == "$.status"
        for difference in result
    )


def test_array_identity_diff_detects_reordering_as_no_change() -> None:
    old = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    new = [{"id": 2, "name": "Bob"}, {"id": 1, "name": "Alice"}]

    positional = compare_json(old, new)
    assert positional != []  # reordering looks like changes by index

    by_identity = compare_json(old, new, array_identity_key="id")
    assert by_identity == []


def test_array_identity_diff_detects_added_and_removed() -> None:
    old = [{"id": 1, "name": "Alice"}]
    new = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    result = compare_json(old, new, array_identity_key="id")

    assert len(result) == 1
    assert result[0].diff_type == DiffType.ADDED
    assert "id=2" in result[0].path


def test_array_identity_diff_detects_field_change_on_matched_item() -> None:
    old = [{"id": 1, "status": "active"}]
    new = [{"id": 1, "status": "inactive"}]

    result = compare_json(old, new, array_identity_key="id")

    assert len(result) == 1
    assert result[0].diff_type == DiffType.CHANGED
    assert result[0].path == "$[id=1].status"


def test_array_identity_diff_falls_back_when_key_missing() -> None:
    old = [{"name": "Alice"}]
    new = [{"name": "Bob"}]

    result = compare_json(old, new, array_identity_key="id")

    assert len(result) == 1
    assert result[0].path == "$[0].name"
