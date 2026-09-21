"""Tests for OpenAPI response-schema extraction."""

from __future__ import annotations

import pytest

from jsonify.core.openapi import OpenApiError, extract_response_schema, list_operations

_DOC = {
    "openapi": "3.1.0",
    "paths": {
        "/users": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserList"}
                            }
                        }
                    }
                }
            }
        },
        "/users/{id}": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/User"}}
                        }
                    },
                    "404": {"content": {"application/json": {"schema": {"type": "object"}}}},
                }
            }
        },
    },
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                "required": ["id"],
            },
            "UserList": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/User"},
            },
        }
    },
}


def test_extract_simple_ref() -> None:
    schema = extract_response_schema(_DOC, path="/users/{id}", method="get", status="200")

    assert schema["type"] == "object"
    assert schema["properties"]["id"] == {"type": "integer"}


def test_extract_nested_ref_in_array() -> None:
    schema = extract_response_schema(_DOC, path="/users", method="get", status="200")

    assert schema["type"] == "array"
    assert schema["items"]["type"] == "object"
    assert schema["items"]["properties"]["name"] == {"type": "string"}


def test_extract_non_default_status() -> None:
    schema = extract_response_schema(_DOC, path="/users/{id}", method="get", status="404")

    assert schema == {"type": "object"}


def test_extract_unknown_path_raises() -> None:
    with pytest.raises(OpenApiError):
        extract_response_schema(_DOC, path="/missing", method="get")


def test_extract_unknown_method_raises() -> None:
    with pytest.raises(OpenApiError):
        extract_response_schema(_DOC, path="/users", method="post")


def test_extract_unknown_status_raises() -> None:
    with pytest.raises(OpenApiError):
        extract_response_schema(_DOC, path="/users", method="get", status="500")


def test_list_operations() -> None:
    operations = list_operations(_DOC)

    assert ("/users", "get") in operations
    assert ("/users/{id}", "get") in operations
    assert len(operations) == 2
