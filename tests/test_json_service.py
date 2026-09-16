"""Tests for the JsonService application service."""

from __future__ import annotations

import json

import pytest

from jsonify.services.json_service import JsonService


@pytest.fixture
def service() -> JsonService:
    """Create a JsonService for each test."""

    return JsonService()


@pytest.fixture
def sample_payload() -> dict:
    """Return a reusable JSON payload."""

    return {
        "company": "Jsonify",
        "departments": [
            {
                "name": "Engineering",
                "members": [
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
        ],
    }


def test_parse(
    service: JsonService,
) -> None:
    """JsonService should parse JSON."""

    raw_json = """
    {
        "name": "Jsonify",
        "active": true
    }
    """

    result = service.parse(raw_json)

    assert result == {
        "name": "Jsonify",
        "active": True,
    }


def test_parse_invalid_json(
    service: JsonService,
) -> None:
    """JsonService should propagate parsing errors."""

    raw_json = """
    {
        "name":
    }
    """

    with pytest.raises(json.JSONDecodeError):
        service.parse(raw_json)


def test_parse_multiple(
    service: JsonService,
) -> None:
    """JsonService should parse consecutive JSON documents."""

    raw_json = """
    {"company": "A"}

    {"company": "B"}

    {"company": "C"}
    """

    result, document_count = service.parse_multiple(
        raw_json
    )

    assert document_count == 3

    assert result == [
        {"company": "A"},
        {"company": "B"},
        {"company": "C"},
    ]


def test_get_unique_keys(
    service: JsonService,
    sample_payload: dict,
) -> None:
    """JsonService should return unique keys."""

    result = service.get_unique_keys(
        sample_payload
    )

    assert result == [
        "active",
        "company",
        "departments",
        "members",
        "name",
    ]


def test_find_by_key(
    service: JsonService,
    sample_payload: dict,
) -> None:
    """JsonService should find values recursively."""

    result = service.find_by_key(
        sample_payload,
        "name",
    )

    assert result == [
        (
            "$.departments[0].name",
            "Engineering",
        ),
        (
            "$.departments[0].members[0].name",
            "Alice",
        ),
        (
            "$.departments[0].members[1].name",
            "Bob",
        ),
    ]


def test_find_by_key_empty_key(
    service: JsonService,
    sample_payload: dict,
) -> None:
    """Empty search keys should return no results."""

    result = service.find_by_key(
        sample_payload,
        "",
    )

    assert result == []


def test_find_by_key_missing(
    service: JsonService,
    sample_payload: dict,
) -> None:
    """Unknown keys should return no results."""

    result = service.find_by_key(
        sample_payload,
        "unknown",
    )

    assert result == []


def test_get_stats(
    service: JsonService,
    sample_payload: dict,
) -> None:
    """JsonService should return JSON statistics."""

    result = service.get_stats(
        sample_payload
    )

    assert result["objects"] == 4
    assert result["arrays"] == 2
    assert result["leaves"] == 6
    assert result["keys"] == 5
    assert result["max_depth"] == 5