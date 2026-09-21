"""HTTP API service for Jsonify."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, cast

import httpx

from jsonify.core.api_request import (
    SUPPORTED_METHODS as _METHODS,
)
from jsonify.core.api_request import (
    ApiRequest,
    apply_variables,
    effective_request,
)
from jsonify.core.diff import JsonDiff, compare_json
from jsonify.core.models import JSONValue


class ApiRequestError(RuntimeError):
    """Raised when an API request cannot be completed."""


class ApiBodyError(ValueError):
    """Raised when a JSON request body is invalid."""


@dataclass(frozen=True, slots=True)
class ApiResponse:
    """Represents an HTTP API response."""

    status_code: int
    reason_phrase: str
    elapsed_ms: float
    headers: dict[str, str]
    content_type: str
    text: str
    json_data: JSONValue | None
    is_json: bool
    url: str
    size_bytes: int = 0

    @property
    def successful(self) -> bool:
        """Return whether the response status is 2xx."""

        return 200 <= self.status_code < 300


@dataclass(frozen=True, slots=True)
class EnvironmentComparison:
    """Result of running one request against two environments."""

    first: ApiResponse
    second: ApiResponse
    differences: list[JsonDiff]


class ApiService:
    """Provides HTTP request functionality."""

    SUPPORTED_METHODS = frozenset(_METHODS)

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def send(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body_text: str = "",
    ) -> ApiResponse:
        """Send a simple request (headers + optional JSON body)."""

        request = ApiRequest(
            method=method,
            url=url,
            headers=list((headers or {}).items()),
            body_kind="json" if body_text.strip() else "none",
            body_text=body_text,
        )

        return self.send_request(request)

    def send_request(
        self,
        request: ApiRequest,
        variables: dict[str, str] | None = None,
    ) -> ApiResponse:
        """Send a full request, substituting environment ``variables`` first.

        Raises:
            ApiRequestError: If the request cannot be completed.
            ApiBodyError: If a JSON request body is invalid.
        """

        if variables:
            request = apply_variables(request, variables)

        effective = effective_request(request)

        if effective.method not in self.SUPPORTED_METHODS:
            raise ApiRequestError(f"Unsupported HTTP method: {request.method}")

        if not effective.url:
            raise ApiRequestError("API URL cannot be empty.")

        if not effective.url.startswith(("http://", "https://")):
            raise ApiRequestError("API URL must start with http:// or https://.")

        if request.body_kind == "json" and request.body_text.strip():
            try:
                json.loads(request.body_text)
            except json.JSONDecodeError as error:
                raise ApiBodyError(
                    f"Invalid JSON request body: {error.msg} "
                    f"(line {error.lineno}, column {error.colno})"
                ) from error

        started = time.perf_counter()

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                response = client.request(
                    method=effective.method,
                    url=effective.url,
                    params=cast(Any, effective.params or None),
                    headers=effective.headers,
                    content=effective.body.encode("utf-8") if effective.body is not None else None,
                )

        except httpx.TimeoutException as error:
            raise ApiRequestError(
                f"The API request timed out after {self._timeout_seconds:g} seconds."
            ) from error

        except httpx.RequestError as error:
            raise ApiRequestError(f"Unable to send API request: {error}") from error

        elapsed_ms = (time.perf_counter() - started) * 1000

        parsed_json: JSONValue | None = None
        is_json = False

        try:
            parsed = response.json()

            if _is_json_value(parsed):
                parsed_json = parsed
                is_json = True

        except (json.JSONDecodeError, ValueError):
            pass

        return ApiResponse(
            status_code=response.status_code,
            reason_phrase=response.reason_phrase,
            elapsed_ms=elapsed_ms,
            headers=dict(response.headers),
            content_type=response.headers.get("content-type", ""),
            text=response.text,
            json_data=parsed_json,
            is_json=is_json,
            url=str(response.url),
            size_bytes=len(response.content),
        )

    def compare_environments(
        self,
        request: ApiRequest,
        first_variables: dict[str, str],
        second_variables: dict[str, str],
    ) -> EnvironmentComparison:
        """Run the same request under two environments and diff the JSON bodies."""

        first = self.send_request(request, first_variables)
        second = self.send_request(request, second_variables)

        first_body: JSONValue = first.json_data if first.is_json else first.text
        second_body: JSONValue = second.json_data if second.is_json else second.text

        return EnvironmentComparison(
            first=first,
            second=second,
            differences=compare_json(first_body, second_body),
        )


def _is_json_value(value: object) -> bool:
    """Return whether a value belongs to the JSON data model."""

    if value is None:
        return True

    if isinstance(value, str | int | float | bool):
        return True

    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)

    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())

    return False
