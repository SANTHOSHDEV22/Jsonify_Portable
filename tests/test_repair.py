"""Tests for best-effort JSON repair."""

from __future__ import annotations

import json

from jsonify.core.repair import attempt_repair


def test_repair_trailing_comma_in_object() -> None:
    result = attempt_repair('{"a": 1, "b": 2,}')

    assert result.is_valid
    assert json.loads(result.text) == {"a": 1, "b": 2}


def test_repair_trailing_comma_in_array() -> None:
    result = attempt_repair("[1, 2, 3,]")

    assert result.is_valid
    assert json.loads(result.text) == [1, 2, 3]


def test_repair_single_quoted_strings() -> None:
    result = attempt_repair("{'a': 'hello'}")

    assert result.is_valid
    assert json.loads(result.text) == {"a": "hello"}


def test_repair_unquoted_keys() -> None:
    result = attempt_repair("{a: 1, b: 2}")

    assert result.is_valid
    assert json.loads(result.text) == {"a": 1, "b": 2}


def test_repair_missing_closing_brace() -> None:
    result = attempt_repair('{"a": 1')

    assert result.is_valid
    assert json.loads(result.text) == {"a": 1}


def test_repair_missing_closing_bracket_nested() -> None:
    result = attempt_repair('{"a": [1, 2')

    assert result.is_valid
    assert json.loads(result.text) == {"a": [1, 2]}


def test_repair_does_not_touch_commas_inside_strings() -> None:
    result = attempt_repair('{"a": "one, two, three"}')

    assert result.is_valid
    assert json.loads(result.text) == {"a": "one, two, three"}


def test_repair_valid_json_is_left_unchanged() -> None:
    original = '{"a": 1, "b": [1, 2, 3]}'
    result = attempt_repair(original)

    assert result.is_valid
    assert result.applied_fixes == []
    assert json.loads(result.text) == json.loads(original)


def test_repair_reports_applied_fixes() -> None:
    result = attempt_repair("{a: 1,}")

    assert result.is_valid
    assert len(result.applied_fixes) >= 1


def test_repair_combined_issues() -> None:
    result = attempt_repair("{a: 'x', b: [1, 2,],")

    assert result.is_valid
    assert json.loads(result.text) == {"a": "x", "b": [1, 2]}
