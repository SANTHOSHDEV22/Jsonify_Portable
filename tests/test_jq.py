"""Tests for the jq-lite query engine."""

from __future__ import annotations

import pytest

from jsonify.core.jq import JqQueryError, run_jq


def test_identity() -> None:
    assert run_jq({"a": 1}, ".") == [{"a": 1}]


def test_field_access() -> None:
    assert run_jq({"a": {"b": 1}}, ".a.b") == [1]


def test_missing_field_returns_null() -> None:
    assert run_jq({"a": 1}, ".missing") == [None]


def test_index_access() -> None:
    assert run_jq({"a": [10, 20, 30]}, ".a[1]") == [20]


def test_negative_index() -> None:
    assert run_jq({"a": [10, 20, 30]}, ".a[-1]") == [30]


def test_out_of_range_index_returns_null() -> None:
    assert run_jq({"a": [1]}, ".a[5]") == [None]


def test_iterate_array() -> None:
    assert run_jq({"a": [1, 2, 3]}, ".a[]") == [1, 2, 3]


def test_iterate_object_values() -> None:
    result = run_jq({"a": 1, "b": 2}, ".[]")
    assert sorted(result) == [1, 2]


def test_pipe_iterate_then_field() -> None:
    payload = {"users": [{"name": "Alice"}, {"name": "Bob"}]}

    assert run_jq(payload, ".users[] | .name") == ["Alice", "Bob"]


def test_keys() -> None:
    assert run_jq({"b": 1, "a": 2}, "keys") == [["a", "b"]]


def test_keys_requires_object() -> None:
    with pytest.raises(JqQueryError):
        run_jq([1, 2], "keys")


def test_length_of_array() -> None:
    assert run_jq([1, 2, 3], "length") == [3]


def test_length_of_string() -> None:
    assert run_jq("hello", "length") == [5]


def test_length_of_number() -> None:
    assert run_jq(-5, "length") == [5]


def test_length_of_null() -> None:
    assert run_jq(None, "length") == [0]


def test_select_equality() -> None:
    payload = {"users": [{"active": True, "name": "A"}, {"active": False, "name": "B"}]}

    result = run_jq(payload, ".users[] | select(.active == true) | .name")

    assert result == ["A"]


def test_select_numeric_comparison() -> None:
    payload = [{"age": 20}, {"age": 30}, {"age": 40}]

    result = run_jq(payload, ".[] | select(.age > 25)")

    assert result == [{"age": 30}, {"age": 40}]


def test_select_string_literal() -> None:
    payload = [{"status": "ok"}, {"status": "error"}]

    result = run_jq(payload, '.[] | select(.status == "error")')

    assert result == [{"status": "error"}]


def test_select_truthy_check() -> None:
    payload = [{"active": True}, {"active": False}, {}]

    result = run_jq(payload, ".[] | select(.active)")

    assert result == [{"active": True}]


def test_map_field() -> None:
    payload = [{"name": "Alice"}, {"name": "Bob"}]

    assert run_jq(payload, "map(.name)") == [["Alice", "Bob"]]


def test_map_requires_array() -> None:
    with pytest.raises(JqQueryError):
        run_jq({"a": 1}, "map(.a)")


def test_full_pipeline() -> None:
    payload = {
        "users": [
            {"name": "Alice", "active": True, "age": 30},
            {"name": "Bob", "active": True, "age": 20},
            {"name": "Carol", "active": False, "age": 40},
        ]
    }

    result = run_jq(payload, ".users[] | select(.active == true) | select(.age > 25) | .name")

    assert result == ["Alice"]


def test_empty_query_raises() -> None:
    with pytest.raises(JqQueryError):
        run_jq({"a": 1}, "")


def test_unsupported_syntax_raises() -> None:
    with pytest.raises(JqQueryError):
        run_jq({"a": 1}, "not_a_real_filter")


def test_iterate_inside_select_raises() -> None:
    with pytest.raises(JqQueryError):
        run_jq([{"a": [1]}], "select(.a[] == 1)")
