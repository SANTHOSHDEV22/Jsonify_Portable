"""JSON Schema validation service for Jsonify."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from jsonify.core.models import JSONValue
from jsonify.core.schema_inference import infer_schema


class JsonSchemaError(ValueError):
    """Raised when the supplied JSON Schema is invalid."""


@dataclass(frozen=True, slots=True)
class SchemaValidationError:
    """Represents one JSON Schema validation failure."""

    path: str
    message: str
    validator: str
    expected: Any
    actual: JSONValue


@dataclass(frozen=True, slots=True)
class SchemaValidationResult:
    """Result of validating a JSON document."""

    valid: bool
    errors: tuple[SchemaValidationError, ...]


class SchemaService:
    """Provides JSON Schema validation operations."""

    def validate(
        self,
        payload: JSONValue,
        schema: dict[str, Any],
    ) -> SchemaValidationResult:
        """
        Validate a JSON payload against a JSON Schema.

        Args:
            payload:
                Parsed JSON document.

            schema:
                Parsed JSON Schema.

        Returns:
            Validation result containing all discovered errors.

        Raises:
            JsonSchemaError:
                If the supplied schema itself is invalid.
        """

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            raise JsonSchemaError(f"Invalid JSON Schema: {error.message}") from error

        validator = Draft202012Validator(schema)

        raw_errors = sorted(
            validator.iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )

        errors = tuple(self._convert_error(error) for error in raw_errors)

        return SchemaValidationResult(
            valid=not errors,
            errors=errors,
        )

    def validate_text(
        self,
        payload_text: str,
        schema_text: str,
    ) -> SchemaValidationResult:
        """
        Parse and validate JSON payload and schema text.

        Raises:
            json.JSONDecodeError:
                If either document contains invalid JSON.

            JsonSchemaError:
                If the schema is valid JSON but is not a valid
                JSON Schema.
        """

        payload: JSONValue = json.loads(payload_text)

        parsed_schema = json.loads(schema_text)

        if not isinstance(parsed_schema, dict):
            raise JsonSchemaError("JSON Schema must be a JSON object.")

        return self.validate(
            payload=payload,
            schema=parsed_schema,
        )

    def generate_schema(
        self,
        payload: JSONValue,
        *,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Infer a JSON Schema (Draft 2020-12) from a sample payload."""

        schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        }

        if title:
            schema["title"] = title

        schema.update(infer_schema(payload))

        return schema

    @staticmethod
    def _convert_error(
        error: Any,
    ) -> SchemaValidationError:
        """Convert jsonschema's validation error to our model."""

        path = SchemaService._format_path(list(error.absolute_path))

        return SchemaValidationError(
            path=path,
            message=error.message,
            validator=str(error.validator),
            expected=error.validator_value,
            actual=error.instance,
        )

    @staticmethod
    def _format_path(
        parts: list[Any],
    ) -> str:
        """Convert validation path components to JSONPath style."""

        path = "$"

        for part in parts:
            if isinstance(part, int):
                path += f"[{part}]"
                continue

            key = str(part)

            if key.isidentifier():
                path += f".{key}"
            else:
                escaped = key.replace("\\", "\\\\").replace('"', '\\"')

                path += f'["{escaped}"]'

        return path
