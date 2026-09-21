"""JSONPath query service for Jsonify."""

from __future__ import annotations

from dataclasses import dataclass

from jsonpath_ng.exceptions import JsonPathParserError
from jsonpath_ng.ext import parse

from jsonify.core.models import JSONValue


class JsonPathQueryError(ValueError):
    """Raised when a JSONPath expression cannot be parsed."""


@dataclass(frozen=True, slots=True)
class JsonPathResult:
    """Represents one JSONPath query result."""

    path: str
    value: JSONValue


class JsonPathService:
    """Provides JSONPath query operations."""

    def query(
        self,
        payload: JSONValue,
        expression: str,
    ) -> list[JsonPathResult]:
        """
        Execute a JSONPath expression against a JSON payload.

        Args:
            payload:
                Parsed JSON payload.

            expression:
                JSONPath expression such as:

                    $.users[*].name

        Returns:
            Matching paths and values.

        Raises:
            JsonPathQueryError:
                If the expression is empty or invalid.
        """

        expression = expression.strip()

        if not expression:
            raise JsonPathQueryError("JSONPath expression cannot be empty.")

        try:
            jsonpath_expression = parse(expression)
        except (JsonPathParserError, Exception) as error:
            raise JsonPathQueryError(f"Invalid JSONPath expression: {expression}") from error

        matches = jsonpath_expression.find(payload)

        results: list[JsonPathResult] = []

        for match in matches:
            results.append(
                JsonPathResult(
                    path=self._format_path(match.full_path),
                    value=match.value,
                )
            )

        return results

    @staticmethod
    def _format_path(path: object) -> str:
        """Convert a jsonpath-ng path into a readable path."""

        path_text = str(path)

        if not path_text:
            return "$"

        if path_text.startswith("$"):
            return path_text

        if path_text.startswith("["):
            return f"${path_text}"

        return f"$.{path_text}"
