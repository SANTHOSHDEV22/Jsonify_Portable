"""Tests for JSON formatting: beautify, minify, normalize."""

from __future__ import annotations

import json

from jsonify.core.formatter import beautify, minify, normalize


def test_beautify_adds_indentation() -> None:
    result = beautify({"a": 1}, indent=2)
    assert result == '{\n  "a": 1\n}'


def test_beautify_sort_keys() -> None:
    result = beautify({"b": 2, "a": 1}, sort_keys=True)
    assert result.index('"a"') < result.index('"b"')


def test_minify_removes_whitespace() -> None:
    result = minify({"a": 1, "b": [1, 2, 3]})
    assert result == '{"a":1,"b":[1,2,3]}'


def test_minify_round_trips() -> None:
    payload = {"a": 1, "b": [1, 2, 3]}
    assert json.loads(minify(payload)) == payload


def test_normalize_sorts_nested_keys() -> None:
    payload = {"b": 1, "a": {"z": 1, "y": 2}}
    result = normalize(payload)
    assert list(result.keys()) == ["a", "b"]
    assert list(result["a"].keys()) == ["y", "z"]


def test_normalize_recurses_into_lists() -> None:
    payload = [{"b": 1, "a": 2}]
    result = normalize(payload)
    assert list(result[0].keys()) == ["a", "b"]


def test_normalize_preserves_scalars() -> None:
    assert normalize(42) == 42
    assert normalize("text") == "text"
    assert normalize(None) is None
