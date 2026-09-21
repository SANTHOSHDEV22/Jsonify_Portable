"""Tests for the breaking-change detector."""

from __future__ import annotations

from jsonify.core.breaking_changes import detect_breaking_changes


def test_removed_property_is_breaking() -> None:
    old = {"a": 1, "b": 2}
    new = {"a": 1}

    changes = detect_breaking_changes(old, new)

    assert len(changes) == 1
    assert changes[0].category == "removed_property"
    assert changes[0].path == "$.b"


def test_type_change_is_breaking() -> None:
    old = {"a": 1}
    new = {"a": "one"}

    changes = detect_breaking_changes(old, new)

    assert len(changes) == 1
    assert changes[0].category == "type_changed"


def test_added_property_without_schema_is_not_breaking() -> None:
    old = {"a": 1}
    new = {"a": 1, "b": 2}

    changes = detect_breaking_changes(old, new)

    assert changes == []


def test_added_required_property_with_schema_is_breaking() -> None:
    old = {"a": 1}
    new = {"a": 1, "b": 2}
    schema = {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a", "b"],
    }

    changes = detect_breaking_changes(old, new, new_schema=schema)

    assert len(changes) == 1
    assert changes[0].category == "new_required_property"
    assert changes[0].path == "$.b"


def test_added_optional_property_with_schema_is_not_breaking() -> None:
    old = {"a": 1}
    new = {"a": 1, "b": 2}
    schema = {
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
        "required": ["a"],
    }

    changes = detect_breaking_changes(old, new, new_schema=schema)

    assert changes == []


def test_nested_required_property_detected() -> None:
    old = {"user": {"name": "Alice"}}
    new = {"user": {"name": "Alice", "email": "alice@example.com"}}
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {"name": {}, "email": {}},
                "required": ["name", "email"],
            }
        },
    }

    changes = detect_breaking_changes(old, new, new_schema=schema)

    assert len(changes) == 1
    assert changes[0].path == "$.user.email"


def test_clean_diff_has_no_breaking_changes() -> None:
    old = {"a": 1}
    new = {"a": 2}

    changes = detect_breaking_changes(old, new)

    assert changes == []
