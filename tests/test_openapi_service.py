"""Tests for the OpenAPI validation service."""

from __future__ import annotations

import pytest

from jsonify.core.openapi import OpenApiError
from jsonify.services.openapi_service import OpenApiService

_DOC = {
    "paths": {
        "/users/{id}": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"id": {"type": "integer"}},
                                    "required": ["id"],
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


def test_validate_response_valid() -> None:
    service = OpenApiService()

    result = service.validate_response(
        {"id": 1}, _DOC, path="/users/{id}", method="get", status="200"
    )

    assert result.valid


def test_validate_response_invalid() -> None:
    service = OpenApiService()

    result = service.validate_response(
        {"id": "not-a-number"}, _DOC, path="/users/{id}", method="get", status="200"
    )

    assert not result.valid
    assert len(result.errors) == 1


def test_validate_response_missing_operation_raises() -> None:
    service = OpenApiService()

    with pytest.raises(OpenApiError):
        service.validate_response({"id": 1}, _DOC, path="/missing", method="get")
