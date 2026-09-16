"""HTTP API service for Jsonify."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx

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

    @property
    def successful(self) -> bool:
        """Return whether the response status is 2xx."""

        return 200 <= self.status_code < 300


class ApiService:
    """Provides HTTP request functionality."""

    SUPPORTED_METHODS = frozenset(
        {
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }
    )

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._timeout_seconds = timeout_seconds

    def send(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body_text: str = "",
    ) -> ApiResponse:
        """
        Send an HTTP request.

        Args:
            method:
                HTTP method.

            url:
                HTTP or HTTPS URL.

            headers:
                Optional HTTP headers.

            body_text:
                Optional JSON request body.

        Returns:
            ApiResponse containing status, timing, headers and body.

        Raises:
            ApiRequestError:
                If the request cannot be completed.

            ApiBodyError:
                If a supplied JSON request body is invalid.
        """

        normalized_method = method.strip().upper()

        if normalized_method not in self.SUPPORTED_METHODS:
            raise ApiRequestError(
                f"Unsupported HTTP method: {method}"
            )

        clean_url = url.strip()

        if not clean_url:
            raise ApiRequestError(
                "API URL cannot be empty."
            )

        if not (
            clean_url.startswith("http://")
            or clean_url.startswith("https://")
        ):
            raise ApiRequestError(
                "API URL must start with http:// or https://."
            )

        request_headers = dict(
            headers or {}
        )

        json_body: JSONValue | None = None

        if body_text.strip():
            try:
                json_body = json.loads(
                    body_text
                )
            except json.JSONDecodeError as error:
                raise ApiBodyError(
                    (
                        "Invalid JSON request body: "
                        f"{error.msg} "
                        f"(line {error.lineno}, "
                        f"column {error.colno})"
                    )
                ) from error

        started = time.perf_counter()

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = client.request(
                    method=normalized_method,
                    url=clean_url,
                    headers=request_headers,
                    json=(
                        json_body
                        if body_text.strip()
                        else None
                    ),
                )

        except httpx.TimeoutException as error:
            raise ApiRequestError(
                (
                    "The API request timed out after "
                    f"{self._timeout_seconds:g} seconds."
                )
            ) from error

        except httpx.RequestError as error:
            raise ApiRequestError(
                f"Unable to send API request: {error}"
            ) from error

        elapsed_ms = (
            time.perf_counter() - started
        ) * 1000

        response_text = response.text

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
            content_type=response.headers.get(
                "content-type",
                "",
            ),
            text=response_text,
            json_data=parsed_json,
            is_json=is_json,
            url=str(response.url),
        )


def _is_json_value(
    value: object,
) -> bool:
    """Return whether a value belongs to the JSON data model."""

    if value is None:
        return True

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return True

    if isinstance(value, list):
        return all(
            _is_json_value(item)
            for item in value
        )

    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and _is_json_value(item)
            for key, item in value.items()
        )

    return False