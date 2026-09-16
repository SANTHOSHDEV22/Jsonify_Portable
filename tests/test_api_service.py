"""Tests for the Jsonify API service."""

from __future__ import annotations

import json

import httpx
import pytest

from jsonify.services.api_service import (
    ApiBodyError,
    ApiRequestError,
    ApiService,
)


def test_get_json_response() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "GET"

        return httpx.Response(
            200,
            json={
                "id": 1,
                "name": "Alice",
            },
        )

    service = ApiService(
        transport=httpx.MockTransport(
            handler
        )
    )

    response = service.send(
        method="GET",
        url="https://example.com/users/1",
    )

    assert response.status_code == 200
    assert response.successful is True
    assert response.is_json is True

    assert response.json_data == {
        "id": 1,
        "name": "Alice",
    }


def test_post_json_body() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"

        body = json.loads(
            request.content
        )

        assert body == {
            "name": "Alice",
        }

        return httpx.Response(
            201,
            json={
                "id": 10,
                "name": "Alice",
            },
        )

    service = ApiService(
        transport=httpx.MockTransport(
            handler
        )
    )

    response = service.send(
        method="POST",
        url="https://example.com/users",
        body_text='{"name": "Alice"}',
    )

    assert response.status_code == 201
    assert response.is_json is True


def test_custom_header() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers["x-test"]
            == "Jsonify"
        )

        return httpx.Response(
            200,
            json={"ok": True},
        )

    service = ApiService(
        transport=httpx.MockTransport(
            handler
        )
    )

    service.send(
        method="GET",
        url="https://example.com",
        headers={
            "X-Test": "Jsonify",
        },
    )


def test_non_json_response() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            text="Hello from server",
            headers={
                "content-type": "text/plain",
            },
        )

    service = ApiService(
        transport=httpx.MockTransport(
            handler
        )
    )

    response = service.send(
        method="GET",
        url="https://example.com",
    )

    assert response.is_json is False
    assert response.json_data is None

    assert (
        response.text
        == "Hello from server"
    )


def test_error_status_is_returned() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "error": "Not found",
            },
        )

    service = ApiService(
        transport=httpx.MockTransport(
            handler
        )
    )

    response = service.send(
        method="GET",
        url="https://example.com/missing",
    )

    assert response.status_code == 404
    assert response.successful is False

    assert response.json_data == {
        "error": "Not found",
    }


def test_invalid_json_body() -> None:
    service = ApiService()

    with pytest.raises(
        ApiBodyError
    ):
        service.send(
            method="POST",
            url="https://example.com",
            body_text="{ invalid json }",
        )


def test_empty_url() -> None:
    service = ApiService()

    with pytest.raises(
        ApiRequestError,
        match="cannot be empty",
    ):
        service.send(
            method="GET",
            url="",
        )


def test_invalid_url_scheme() -> None:
    service = ApiService()

    with pytest.raises(
        ApiRequestError,
        match="http",
    ):
        service.send(
            method="GET",
            url="example.com/api",
        )


def test_unsupported_method() -> None:
    service = ApiService()

    with pytest.raises(
        ApiRequestError,
        match="Unsupported",
    ):
        service.send(
            method="CONNECT",
            url="https://example.com",
        )


def test_response_headers() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": True},
            headers={
                "X-Request-Id": "abc123",
            },
        )

    service = ApiService(
        transport=httpx.MockTransport(
            handler
        )
    )

    response = service.send(
        method="GET",
        url="https://example.com",
    )

    assert (
        response.headers["x-request-id"]
        == "abc123"
    )


def test_json_array_response() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                },
                {
                    "id": 2,
                },
            ],
        )

    service = ApiService(
        transport=httpx.MockTransport(
            handler
        )
    )

    response = service.send(
        method="GET",
        url="https://example.com/users",
    )

    assert response.is_json is True

    assert response.json_data == [
        {"id": 1},
        {"id": 2},
    ]