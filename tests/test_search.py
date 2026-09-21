"""Tests for JSON key/value search."""

from __future__ import annotations

from jsonify.core.search import search_json


def test_search_by_key() -> None:
    payload = {"name": "Alice", "age": 30}

    matches = search_json(payload, "name", target="key")

    assert len(matches) == 1
    assert matches[0].segments == ["name"]
    assert matches[0].matched_key is True


def test_search_by_value() -> None:
    payload = {"name": "Alice", "city": "Alicetown"}

    matches = search_json(payload, "Alice", target="value")

    assert len(matches) == 2


def test_search_both_targets() -> None:
    payload = {"key": "value"}

    matches = search_json(payload, "key", target="both")

    assert len(matches) == 1
    assert matches[0].matched_key is True


def test_search_case_insensitive_by_default() -> None:
    payload = {"Name": "Alice"}

    matches = search_json(payload, "name", target="key")

    assert len(matches) == 1


def test_search_case_sensitive() -> None:
    payload = {"Name": "Alice"}

    matches = search_json(payload, "name", target="key", case_sensitive=True)

    assert matches == []


def test_search_regex() -> None:
    payload = {"a": "abc123", "b": "xyz"}

    matches = search_json(payload, r"^[a-z]+\d+$", target="value", use_regex=True)

    assert len(matches) == 1
    assert matches[0].segments == ["a"]


def test_search_invalid_regex_returns_empty() -> None:
    matches = search_json({"a": 1}, "(unclosed", target="key", use_regex=True)

    assert matches == []


def test_search_inside_array() -> None:
    payload = {"users": [{"name": "Alice"}, {"name": "Bob"}]}

    matches = search_json(payload, "Bob", target="value")

    assert len(matches) == 1
    assert matches[0].segments == ["users", 1, "name"]


def test_search_empty_query_returns_no_matches() -> None:
    assert search_json({"a": 1}, "", target="both") == []


def test_search_does_not_match_containers() -> None:
    payload = {"nested": {"a": 1}}

    matches = search_json(payload, "nested", target="value")

    assert matches == []
