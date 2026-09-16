"""High-level JSON operations used by the application."""

from __future__ import annotations

from jsonify.core.models import JSONPathMatch, JSONValue
from jsonify.core.parser import parse_json, parse_multiple_json
from jsonify.core.traversal import (
    calculate_json_stats,
    extract_unique_keys,
    find_values_by_key,
)


class JsonService:
    """
    Provides high-level JSON operations for the UI layer.

    The service coordinates functionality from the core package so
    UI components do not need to depend directly on parsing and
    traversal implementations.
    """

    def parse(self, raw_text: str) -> JSONValue:
        """
        Parse a single JSON document.

        Args:
            raw_text: Raw JSON text.

        Returns:
            Parsed JSON data.

        Raises:
            json.JSONDecodeError: If the JSON is invalid.
        """
        return parse_json(raw_text)

    def parse_multiple(
        self,
        raw_text: str,
    ) -> tuple[JSONValue, int]:
        """
        Parse one or more consecutive JSON documents.

        Args:
            raw_text: Raw JSON text.

        Returns:
            A tuple containing:
            - Parsed JSON data.
            - Number of parsed documents.

        Raises:
            json.JSONDecodeError: If the JSON is invalid.
        """
        return parse_multiple_json(raw_text)

    def get_unique_keys(
        self,
        payload: JSONValue,
    ) -> list[str]:
        """
        Return all unique keys in the JSON payload.

        Args:
            payload: Parsed JSON data.

        Returns:
            Sorted list of unique keys.
        """
        return extract_unique_keys(payload)

    def find_by_key(
        self,
        payload: JSONValue,
        key: str,
    ) -> list[JSONPathMatch]:
        """
        Find every occurrence of a key in the JSON payload.

        Args:
            payload: Parsed JSON data.
            key: Key to search for.

        Returns:
            List of JSON path and value pairs.
        """
        if not key:
            return []

        return find_values_by_key(
            payload,
            key,
        )

    def get_stats(
        self,
        payload: JSONValue,
    ) -> dict[str, int]:
        """
        Calculate structural statistics for the JSON payload.

        Args:
            payload: Parsed JSON data.

        Returns:
            Dictionary containing JSON statistics.
        """
        return calculate_json_stats(payload)
