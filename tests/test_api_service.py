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

    service = ApiService(transport=httpx.MockTransport(handler))

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

        body = json.loads(request.content)

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

    service = ApiService(transport=httpx.MockTransport(handler))

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
        assert request.headers["x-test"] == "Jsonify"

        return httpx.Response(
            200,
            json={"ok": True},
        )

    service = ApiService(transport=httpx.MockTransport(handler))

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

    service = ApiService(transport=httpx.MockTransport(handler))

    response = service.send(
        method="GET",
        url="https://example.com",
    )

    assert response.is_json is False
    assert response.json_data is None

    assert response.text == "Hello from server"


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

    service = ApiService(transport=httpx.MockTransport(handler))

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

    with pytest.raises(ApiBodyError):
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

    service = ApiService(transport=httpx.MockTransport(handler))

    response = service.send(
        method="GET",
        url="https://example.com",
    )

    assert response.headers["x-request-id"] == "abc123"


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

    service = ApiService(transport=httpx.MockTransport(handler))

    response = service.send(
        method="GET",
        url="https://example.com/users",
    )

    assert response.is_json is True

    assert response.json_data == [
        {"id": 1},
        {"id": 2},
    ]


def _echo_service() -> ApiService:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": request.content.decode(),
            },
        )

    return ApiService(transport=httpx.MockTransport(handler))


def test_head_and_options_supported() -> None:
    service = _echo_service()

    assert service.send(method="HEAD", url="https://x.test").status_code == 200
    assert service.send(method="OPTIONS", url="https://x.test").status_code == 200


def test_send_request_params_auth_and_size() -> None:
    from jsonify.core.api_request import ApiAuth, ApiRequest

    request = ApiRequest(
        method="GET",
        url="https://x.test/a",
        params=[("q", "1")],
        auth=ApiAuth(kind="bearer", token="tok"),
    )

    response = _echo_service().send_request(request)

    assert "q=1" in response.json_data["url"]
    assert response.json_data["headers"]["authorization"] == "Bearer tok"
    assert response.size_bytes > 0


def test_send_request_form_body() -> None:
    from jsonify.core.api_request import ApiRequest

    request = ApiRequest(
        method="POST", url="https://x.test", body_kind="form", form_fields=[("a", "1")]
    )

    response = _echo_service().send_request(request)

    assert response.json_data["body"] == "a=1"
    assert response.json_data["headers"]["content-type"] == "application/x-www-form-urlencoded"


def test_send_request_applies_environment_variables() -> None:
    from jsonify.core.api_request import ApiRequest

    response = _echo_service().send_request(
        ApiRequest(url="{{base}}/x"), {"base": "https://dev.test"}
    )

    assert response.json_data["url"] == "https://dev.test/x"


def test_compare_environments_reports_differences() -> None:
    from jsonify.core.api_request import ApiRequest

    result = _echo_service().compare_environments(
        ApiRequest(url="{{base}}/x"), {"base": "https://dev.test"}, {"base": "https://prod.test"}
    )

    assert any("url" in d.path for d in result.differences)
