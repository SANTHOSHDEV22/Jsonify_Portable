"""Tests for the JSONPath service."""

from __future__ import annotations

import pytest

from jsonify.services.jsonpath_service import (
    JsonPathQueryError,
    JsonPathService,
)


@pytest.fixture
def service() -> JsonPathService:
    """Create a JSONPath service."""

    return JsonPathService()


@pytest.fixture
def payload() -> dict:
    """Create reusable test JSON."""

    return {
        "company": "Jsonify",
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "active": True,
            },
            {
                "id": 2,
                "name": "Bob",
                "active": False,
            },
            {
                "id": 3,
                "name": "Charlie",
                "active": True,
            },
        ],
        "department": {
            "name": "Engineering",
            "manager": {
                "name": "David",
            },
        },
    }


def test_root_query(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$",
    )

    assert len(results) == 1
    assert results[0].value == payload


def test_array_names(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$.users[*].name",
    )

    assert [
        result.value
        for result in results
    ] == [
        "Alice",
        "Bob",
        "Charlie",
    ]


def test_array_ids(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$.users[*].id",
    )

    assert [
        result.value
        for result in results
    ] == [
        1,
        2,
        3,
    ]


def test_recursive_name_search(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$..name",
    )

    values = [
        result.value
        for result in results
    ]

    assert "Alice" in values
    assert "Bob" in values
    assert "Charlie" in values
    assert "Engineering" in values
    assert "David" in values


def test_nested_property(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$.department.manager.name",
    )

    assert len(results) == 1

    assert results[0].value == "David"


def test_no_matches(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$.missing.value",
    )

    assert results == []


def test_empty_expression(
    service: JsonPathService,
    payload: dict,
) -> None:
    with pytest.raises(
        JsonPathQueryError
    ):
        service.query(
            payload,
            "",
        )


def test_whitespace_expression(
    service: JsonPathService,
    payload: dict,
) -> None:
    with pytest.raises(
        JsonPathQueryError
    ):
        service.query(
            payload,
            "     ",
        )


def test_invalid_expression(
    service: JsonPathService,
    payload: dict,
) -> None:
    with pytest.raises(
        JsonPathQueryError
    ):
        service.query(
            payload,
            "$.users[[",
        )


def test_filter_expression(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$.users[?(@.active == true)].name",
    )

    assert [
        result.value
        for result in results
    ] == [
        "Alice",
        "Charlie",
    ]


def test_result_contains_path(
    service: JsonPathService,
    payload: dict,
) -> None:
    results = service.query(
        payload,
        "$.users[*].name",
    )

    assert len(results) == 3

    assert all(
        result.path.startswith("$")
        for result in results
    )