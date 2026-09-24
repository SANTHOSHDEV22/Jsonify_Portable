"""Tests for the AI chat-completions service (network mocked)."""

from __future__ import annotations

import httpx
import pytest

from jsonify.core.ai_provider import AiProviderConfig
from jsonify.services.ai_service import AiNotConfiguredError, AiRequestError, AiService


def test_not_configured_raises_without_any_network_attempt() -> None:
    service = AiService(AiProviderConfig())

    with pytest.raises(AiNotConfiguredError):
        service.complete([{"role": "user", "content": "hi"}])


def test_complete_returns_message_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.openai.com/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello there"}}]})

    config = AiProviderConfig(
        base_url="https://api.openai.com/v1", api_key="sk-1", model="gpt-4o-mini"
    )
    service = AiService(config, transport=httpx.MockTransport(handler))

    result = service.complete([{"role": "user", "content": "hi"}])

    assert result == "hello there"


def test_complete_sends_bearer_token_when_api_key_set() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-1"
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    config = AiProviderConfig(base_url="https://api.openai.com/v1", api_key="sk-1", model="m")
    AiService(config, transport=httpx.MockTransport(handler)).complete([])


def test_complete_omits_auth_header_when_no_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    config = AiProviderConfig(base_url="http://localhost:11434/v1", model="llama3")
    AiService(config, transport=httpx.MockTransport(handler)).complete([])


def test_http_error_raises_ai_request_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    config = AiProviderConfig(base_url="https://api.openai.com/v1", model="m")
    service = AiService(config, transport=httpx.MockTransport(handler))

    with pytest.raises(AiRequestError, match="500"):
        service.complete([])


def test_malformed_response_raises_ai_request_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    config = AiProviderConfig(base_url="https://api.openai.com/v1", model="m")
    service = AiService(config, transport=httpx.MockTransport(handler))

    with pytest.raises(AiRequestError, match="unexpected response shape"):
        service.complete([])


def test_network_error_raises_ai_request_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    config = AiProviderConfig(base_url="http://localhost:11434/v1", model="llama3")
    service = AiService(config, transport=httpx.MockTransport(handler))

    with pytest.raises(AiRequestError, match="Unable to reach"):
        service.complete([])
