"""Tests for hierarchy-preserving JSON filtering."""

from __future__ import annotations

from jsonify.core.filter import FilterCriteria, filter_json


def test_filter_empty_criteria_returns_original() -> None:
    payload = {"a": 1}
    assert filter_json(payload, FilterCriteria()) is payload


def test_filter_by_key_preserves_ancestors() -> None:
    payload = {
        "company": {
            "department": {
                "name": "Engineering",
                "size": 10,
            }
        }
    }

    result = filter_json(payload, FilterCriteria(key_contains="name"))

    assert result == {"company": {"department": {"name": "Engineering"}}}


def test_filter_by_value_substring() -> None:
    payload = {
        "users": [
            {"name": "Alice"},
            {"name": "Bob"},
        ]
    }

    result = filter_json(payload, FilterCriteria(value_contains="Ali"))

    assert result == {"users": [{"name": "Alice"}]}


def test_filter_by_type() -> None:
    payload = {"a": 1, "b": "text", "c": True}

    result = filter_json(payload, FilterCriteria(type_name="string"))

    assert result == {"b": "text"}


def test_filter_no_matches_returns_none() -> None:
    payload = {"a": 1}

    result = filter_json(payload, FilterCriteria(key_contains="nope"))

    assert result is None


def test_filter_case_insensitive_by_default() -> None:
    payload = {"Name": "Alice"}

    result = filter_json(payload, FilterCriteria(key_contains="name"))

    assert result == {"Name": "Alice"}


def test_filter_case_sensitive() -> None:
    payload = {"Name": "Alice"}

    result = filter_json(payload, FilterCriteria(key_contains="name", case_sensitive=True))

    assert result is None
