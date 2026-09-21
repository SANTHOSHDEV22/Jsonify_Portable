"""Tests for JSON parsing utilities."""

from __future__ import annotations

import json

import pytest

from jsonify.core.parser import find_duplicate_keys, parse_json, parse_multiple_json


def test_parse_json_object() -> None:
    """Parse a standard JSON object."""

    raw_json = """
    {
        "name": "Santhosh",
        "age": 22,
        "active": true
    }
    """

    result = parse_json(raw_json)

    assert result == {
        "name": "Santhosh",
        "age": 22,
        "active": True,
    }


def test_parse_json_array() -> None:
    """Parse a top-level JSON array."""

    raw_json = """
    [
        {"id": 1},
        {"id": 2},
        {"id": 3}
    ]
    """

    result = parse_json(raw_json)

    assert result == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]


def test_parse_nested_json() -> None:
    """Parse deeply nested JSON."""

    raw_json = """
    {
        "company": "Jsonify",
        "department": {
            "name": "Engineering",
            "employees": [
                {
                    "name": "Alice",
                    "active": true
                },
                {
                    "name": "Bob",
                    "active": false
                }
            ]
        }
    }
    """

    result = parse_json(raw_json)

    assert isinstance(result, dict)

    assert result["company"] == "Jsonify"

    department = result["department"]

    assert isinstance(department, dict)
    assert department["name"] == "Engineering"

    employees = department["employees"]

    assert isinstance(employees, list)
    assert len(employees) == 2


def test_parse_json_null() -> None:
    """Parse a JSON null value."""

    result = parse_json("null")

    assert result is None


def test_parse_json_boolean() -> None:
    """Parse JSON boolean values."""

    assert parse_json("true") is True
    assert parse_json("false") is False


def test_parse_json_number() -> None:
    """Parse JSON numbers."""

    assert parse_json("42") == 42
    assert parse_json("10.5") == 10.5


def test_parse_json_string() -> None:
    """Parse a JSON string."""

    result = parse_json('"Jsonify"')

    assert result == "Jsonify"


def test_parse_invalid_json() -> None:
    """Invalid JSON should raise JSONDecodeError."""

    raw_json = """
    {
        "name": "Jsonify",
    }
    """

    with pytest.raises(json.JSONDecodeError):
        parse_json(raw_json)


def test_parse_empty_json() -> None:
    """Empty input should raise JSONDecodeError."""

    with pytest.raises(json.JSONDecodeError):
        parse_json("")


def test_parse_multiple_json_objects() -> None:
    """Parse multiple consecutive JSON objects."""

    raw_json = """
    {
        "company": "Company A"
    }

    {
        "company": "Company B"
    }

    {
        "company": "Company C"
    }
    """

    result, document_count = parse_multiple_json(raw_json)

    assert document_count == 3

    assert isinstance(result, list)

    assert result == [
        {"company": "Company A"},
        {"company": "Company B"},
        {"company": "Company C"},
    ]


def test_parse_multiple_single_document() -> None:
    """A single document should be returned directly."""

    raw_json = """
    {
        "name": "Jsonify"
    }
    """

    result, document_count = parse_multiple_json(raw_json)

    assert document_count == 1

    assert result == {
        "name": "Jsonify",
    }


def test_parse_multiple_with_whitespace() -> None:
    """Whitespace between JSON documents should be ignored."""

    raw_json = """

        {"id": 1}


        {"id": 2}


    """

    result, document_count = parse_multiple_json(raw_json)

    assert document_count == 2

    assert result == [
        {"id": 1},
        {"id": 2},
    ]


def test_parse_multiple_with_commas() -> None:
    """Commas between independent JSON documents are supported."""

    raw_json = """
    {"id": 1},
    {"id": 2},
    {"id": 3}
    """

    result, document_count = parse_multiple_json(raw_json)

    assert document_count == 3

    assert result == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]


def test_parse_multiple_invalid_json() -> None:
    """Invalid input should raise JSONDecodeError."""

    raw_json = """
    {"id": 1}

    {"id": }
    """

    with pytest.raises(json.JSONDecodeError):
        parse_multiple_json(raw_json)


def test_parse_multiple_empty_input() -> None:
    """Empty multiple-document input should fail."""

    with pytest.raises(json.JSONDecodeError):
        parse_multiple_json("")


def test_find_duplicate_keys_none() -> None:
    """No duplicate keys should produce no messages."""

    assert find_duplicate_keys('{"a": 1, "b": 2}') == []


def test_find_duplicate_keys_simple() -> None:
    """A repeated key in the same object should be reported."""

    messages = find_duplicate_keys('{"a": 1, "a": 2}')

    assert len(messages) == 1
    assert "a" in messages[0]


def test_find_duplicate_keys_nested() -> None:
    """Duplicate keys should be detected at any nesting level."""

    raw_json = '{"outer": {"x": 1, "x": 2}, "y": 1, "y": 2}'

    messages = find_duplicate_keys(raw_json)

    assert len(messages) == 2


def test_find_duplicate_keys_invalid_json() -> None:
    """Invalid JSON should return no messages rather than raising."""

    assert find_duplicate_keys("{not valid") == []
