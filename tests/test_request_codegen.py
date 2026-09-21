"""Tests for HTTP request code generation."""

from __future__ import annotations

import pytest

from jsonify.core.api_request import ApiAuth, ApiRequest
from jsonify.core.request_codegen import generate_request_code

_REQUEST = ApiRequest(
    method="POST",
    url="https://api.test/users",
    headers=[("X-Test", "y")],
    auth=ApiAuth(kind="bearer", token="abc"),
    body_kind="json",
    body_text='{"name": "Alice"}',
)


def test_python_snippet() -> None:
    code = generate_request_code(_REQUEST, "python")

    assert "import requests" in code
    assert "requests.request(" in code
    assert "Bearer abc" in code


def test_javascript_snippet() -> None:
    code = generate_request_code(_REQUEST, "javascript")

    assert "await fetch(" in code
    assert '"POST"' in code


def test_csharp_snippet() -> None:
    code = generate_request_code(_REQUEST, "csharp")

    assert "HttpClient" in code
    assert "StringContent" in code


def test_java_snippet() -> None:
    code = generate_request_code(_REQUEST, "java")

    assert "HttpRequest.newBuilder()" in code
    assert "BodyPublishers.ofString" in code


def test_get_without_body() -> None:
    code = generate_request_code(ApiRequest(url="https://x.test"), "java")

    assert "noBody()" in code


def test_unsupported_language() -> None:
    with pytest.raises(ValueError):
        generate_request_code(_REQUEST, "cobol")
