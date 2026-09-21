"""Tests for large JSON analysis."""

from __future__ import annotations

from jsonify.core.large_json import (
    analyze_json,
)


def test_simple_object() -> None:
    payload = {
        "name": "Alice",
        "age": 25,
    }

    result = analyze_json(payload)

    assert result.total_nodes == 3
    assert result.containers == 1
    assert result.primitives == 2
    assert result.max_depth == 1


def test_nested_object() -> None:
    payload = {
        "user": {
            "profile": {
                "name": "Alice",
            }
        }
    }

    result = analyze_json(payload)

    assert result.total_nodes == 4
    assert result.containers == 3
    assert result.primitives == 1
    assert result.max_depth == 3


def test_array() -> None:
    payload = [
        1,
        2,
        3,
    ]

    result = analyze_json(payload)

    assert result.total_nodes == 4
    assert result.containers == 1
    assert result.primitives == 3


def test_nested_array() -> None:
    payload = {
        "users": [
            {
                "id": 1,
            },
            {
                "id": 2,
            },
        ]
    }

    result = analyze_json(payload)

    assert result.total_nodes == 6
    assert result.containers == 4
    assert result.primitives == 2
    assert result.max_depth == 3


def test_null() -> None:
    result = analyze_json(None)

    assert result.total_nodes == 1
    assert result.containers == 0
    assert result.primitives == 1


def test_deep_json_does_not_use_recursion() -> None:
    payload = None

    for _ in range(2_000):
        payload = {
            "child": payload,
        }

    result = analyze_json(payload)

    assert result.total_nodes == 2_001
    assert result.max_depth == 2_000
