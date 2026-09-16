"""Tests for JSON traversal utilities."""

from __future__ import annotations

from jsonify.core.traversal import (
    calculate_json_stats,
    extract_unique_keys,
    find_values_by_key,
)


def test_extract_unique_keys_from_object() -> None:
    """Extract keys from a simple object."""

    payload = {
        "name": "Alice",
        "age": 25,
        "active": True,
    }

    result = extract_unique_keys(payload)

    assert result == [
        "active",
        "age",
        "name",
    ]


def test_extract_unique_keys_nested() -> None:
    """Extract keys recursively from nested structures."""

    payload = {
        "company": "Jsonify",
        "department": {
            "name": "Engineering",
            "employees": [
                {
                    "name": "Alice",
                    "role": "Developer",
                },
                {
                    "name": "Bob",
                    "role": "Tester",
                },
            ],
        },
    }

    result = extract_unique_keys(payload)

    assert result == [
        "company",
        "department",
        "employees",
        "name",
        "role",
    ]


def test_extract_unique_keys_removes_duplicates() -> None:
    """Duplicate keys should appear only once."""

    payload = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
            },
            {
                "id": 2,
                "name": "Bob",
            },
        ]
    }

    result = extract_unique_keys(payload)

    assert result == [
        "id",
        "name",
        "users",
    ]


def test_extract_unique_keys_empty_object() -> None:
    """Empty object should produce no keys."""

    result = extract_unique_keys({})

    assert result == []


def test_extract_unique_keys_empty_array() -> None:
    """Empty array should produce no keys."""

    result = extract_unique_keys([])

    assert result == []


def test_find_values_by_key_simple() -> None:
    """Find a key in a simple object."""

    payload = {
        "name": "Alice",
        "age": 25,
    }

    result = find_values_by_key(
        payload,
        "name",
    )

    assert result == [
        ("$.name", "Alice"),
    ]


def test_find_values_by_key_nested() -> None:
    """Find the same key at multiple nesting levels."""

    payload = {
        "name": "Company",
        "department": {
            "name": "Engineering",
            "employee": {
                "name": "Alice",
            },
        },
    }

    result = find_values_by_key(
        payload,
        "name",
    )

    assert result == [
        ("$.name", "Company"),
        ("$.department.name", "Engineering"),
        ("$.department.employee.name", "Alice"),
    ]


def test_find_values_by_key_inside_array() -> None:
    """Find keys inside arrays."""

    payload = {
        "employees": [
            {
                "name": "Alice",
            },
            {
                "name": "Bob",
            },
        ]
    }

    result = find_values_by_key(
        payload,
        "name",
    )

    assert result == [
        ("$.employees[0].name", "Alice"),
        ("$.employees[1].name", "Bob"),
    ]


def test_find_values_by_key_not_found() -> None:
    """Missing keys should return an empty list."""

    payload = {
        "name": "Alice",
    }

    result = find_values_by_key(
        payload,
        "missing",
    )

    assert result == []


def test_find_values_returns_container() -> None:
    """Searching may return an object or array value."""

    payload = {
        "company": {
            "name": "Jsonify",
        }
    }

    result = find_values_by_key(
        payload,
        "company",
    )

    assert result == [
        (
            "$.company",
            {
                "name": "Jsonify",
            },
        ),
    ]


def test_calculate_json_stats_simple_object() -> None:
    """Calculate statistics for a simple object."""

    payload = {
        "name": "Alice",
        "age": 25,
    }

    result = calculate_json_stats(payload)

    assert result["objects"] == 1
    assert result["arrays"] == 0
    assert result["leaves"] == 2
    assert result["keys"] == 2
    assert result["max_depth"] == 1


def test_calculate_json_stats_nested() -> None:
    """Calculate statistics for nested JSON."""

    payload = {
        "company": "Jsonify",
        "employees": [
            {
                "name": "Alice",
                "active": True,
            },
            {
                "name": "Bob",
                "active": False,
            },
        ],
    }

    result = calculate_json_stats(payload)

    assert result["objects"] == 3
    assert result["arrays"] == 1
    assert result["leaves"] == 5

    assert result["keys"] == 4

    assert result["max_depth"] == 3


def test_calculate_json_stats_empty_object() -> None:
    """Statistics should work for an empty object."""

    result = calculate_json_stats({})

    assert result == {
        "objects": 1,
        "arrays": 0,
        "leaves": 0,
        "max_depth": 0,
        "keys": 0,
    }


def test_calculate_json_stats_empty_array() -> None:
    """Statistics should work for an empty array."""

    result = calculate_json_stats([])

    assert result == {
        "objects": 0,
        "arrays": 1,
        "leaves": 0,
        "max_depth": 0,
        "keys": 0,
    }


def test_calculate_json_stats_primitive() -> None:
    """Statistics should work for a primitive root value."""

    result = calculate_json_stats("Jsonify")

    assert result == {
        "objects": 0,
        "arrays": 0,
        "leaves": 1,
        "max_depth": 0,
        "keys": 0,
    }