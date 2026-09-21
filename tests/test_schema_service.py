"""Tests for JSON Schema validation."""

from __future__ import annotations

import pytest

from jsonify.services.schema_service import (
    JsonSchemaError,
    SchemaService,
)


@pytest.fixture
def service() -> SchemaService:
    """Create a schema service."""

    return SchemaService()


@pytest.fixture
def user_schema() -> dict:
    """Create reusable user schema."""

    return {
        "$schema": ("https://json-schema.org/draft/2020-12/schema"),
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
            },
            "name": {
                "type": "string",
            },
            "age": {
                "type": "integer",
                "minimum": 18,
            },
            "active": {
                "type": "boolean",
            },
        },
        "required": [
            "id",
            "name",
        ],
        "additionalProperties": False,
    }


def test_valid_payload(
    service: SchemaService,
    user_schema: dict,
) -> None:
    payload = {
        "id": 1,
        "name": "Alice",
        "age": 25,
        "active": True,
    }

    result = service.validate(
        payload,
        user_schema,
    )

    assert result.valid is True
    assert result.errors == ()


def test_invalid_integer_type(
    service: SchemaService,
    user_schema: dict,
) -> None:
    payload = {
        "id": "1",
        "name": "Alice",
    }

    result = service.validate(
        payload,
        user_schema,
    )

    assert result.valid is False
    assert len(result.errors) == 1

    error = result.errors[0]

    assert error.path == "$.id"
    assert error.validator == "type"
    assert error.expected == "integer"
    assert error.actual == "1"


def test_missing_required_property(
    service: SchemaService,
    user_schema: dict,
) -> None:
    payload = {
        "id": 1,
    }

    result = service.validate(
        payload,
        user_schema,
    )

    assert result.valid is False

    assert any(error.validator == "required" for error in result.errors)


def test_minimum_value(
    service: SchemaService,
    user_schema: dict,
) -> None:
    payload = {
        "id": 1,
        "name": "Alice",
        "age": 15,
    }

    result = service.validate(
        payload,
        user_schema,
    )

    assert result.valid is False

    assert any(error.path == "$.age" and error.validator == "minimum" for error in result.errors)


def test_additional_property(
    service: SchemaService,
    user_schema: dict,
) -> None:
    payload = {
        "id": 1,
        "name": "Alice",
        "unknown": "value",
    }

    result = service.validate(
        payload,
        user_schema,
    )

    assert result.valid is False

    assert any(error.validator == "additionalProperties" for error in result.errors)


def test_nested_validation(
    service: SchemaService,
) -> None:
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "age": {
                        "type": "integer",
                    }
                },
            }
        },
    }

    payload = {
        "user": {
            "age": "twenty-five",
        }
    }

    result = service.validate(
        payload,
        schema,
    )

    assert result.valid is False
    assert result.errors[0].path == "$.user.age"


def test_array_validation(
    service: SchemaService,
) -> None:
    schema = {
        "type": "array",
        "items": {
            "type": "integer",
        },
    }

    payload = [
        1,
        2,
        "three",
        4,
    ]

    result = service.validate(
        payload,
        schema,
    )

    assert result.valid is False
    assert result.errors[0].path == "$[2]"


def test_multiple_errors(
    service: SchemaService,
    user_schema: dict,
) -> None:
    payload = {
        "id": "wrong",
        "name": 100,
        "age": 10,
    }

    result = service.validate(
        payload,
        user_schema,
    )

    assert result.valid is False
    assert len(result.errors) == 3


def test_invalid_schema(
    service: SchemaService,
) -> None:
    schema = {
        "type": "not-a-real-type",
    }

    with pytest.raises(JsonSchemaError):
        service.validate(
            {},
            schema,
        )


def test_validate_text(
    service: SchemaService,
) -> None:
    payload = """
    {
        "name": "Alice"
    }
    """

    schema = """
    {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            }
        },
        "required": ["name"]
    }
    """

    result = service.validate_text(
        payload,
        schema,
    )

    assert result.valid is True


def test_schema_must_be_object(
    service: SchemaService,
) -> None:
    with pytest.raises(JsonSchemaError):
        service.validate_text(
            "{}",
            "[]",
        )
