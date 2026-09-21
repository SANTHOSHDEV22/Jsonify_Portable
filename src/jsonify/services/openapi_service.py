"""Validate a JSON payload against an OpenAPI document's response schema."""

from __future__ import annotations

import json
from typing import Any

from jsonify.core.models import JSONValue
from jsonify.core.openapi import OpenApiError, extract_response_schema, list_operations
from jsonify.services.schema_service import (
    JsonSchemaError,
    SchemaService,
    SchemaValidationResult,
)


class OpenApiService:
    """Provides OpenAPI response-schema validation for the UI layer."""

    def __init__(self, schema_service: SchemaService | None = None) -> None:
        self._schema_service = schema_service if schema_service is not None else SchemaService()

    def list_operations(self, openapi_doc: dict[str, Any]) -> list[tuple[str, str]]:
        """List every (path, method) operation defined in the document."""

        return list_operations(openapi_doc)

    def validate_response(
        self,
        payload: JSONValue,
        openapi_doc: dict[str, Any],
        *,
        path: str,
        method: str,
        status: str = "200",
    ) -> SchemaValidationResult:
        """Validate ``payload`` against the schema for one OpenAPI operation.

        Raises:
            OpenApiError: If the operation/response/schema can't be found.
            JsonSchemaError: If the extracted schema is itself invalid.
        """

        schema = extract_response_schema(openapi_doc, path=path, method=method, status=status)
        return self._schema_service.validate(payload, schema)

    def validate_response_text(
        self,
        payload_text: str,
        openapi_text: str,
        *,
        path: str,
        method: str,
        status: str = "200",
    ) -> SchemaValidationResult:
        """Parse and validate payload/OpenAPI-document text.

        Raises:
            json.JSONDecodeError: If either document isn't valid JSON.
            OpenApiError: If the operation/response/schema can't be found.
            JsonSchemaError: If the extracted schema is itself invalid.
        """

        payload: JSONValue = json.loads(payload_text)
        openapi_doc = json.loads(openapi_text)

        if not isinstance(openapi_doc, dict):
            raise OpenApiError("OpenAPI document must be a JSON object.")

        return self.validate_response(payload, openapi_doc, path=path, method=method, status=status)


__all__ = ["OpenApiService", "OpenApiError", "JsonSchemaError"]
