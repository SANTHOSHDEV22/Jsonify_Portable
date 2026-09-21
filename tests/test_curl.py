"""Tests for cURL import/export."""

from __future__ import annotations

import pytest

from jsonify.core.api_request import ApiAuth, ApiRequest
from jsonify.core.curl import CurlParseError, parse_curl, to_curl


def test_parse_simple_get() -> None:
    request = parse_curl("curl https://api.test/users")

    assert request.method == "GET"
    assert request.url == "https://api.test/users"


def test_parse_query_string_into_params() -> None:
    request = parse_curl("curl 'https://api.test/users?page=2&q=a'")

    assert request.url == "https://api.test/users"
    assert request.params == [("page", "2"), ("q", "a")]


def test_parse_post_json_body_and_headers() -> None:
    request = parse_curl(
        "curl -X POST https://api.test/users \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        '  -d \'{"name": "Alice"}\''
    )

    assert request.method == "POST"
    assert request.body_kind == "json"
    assert request.body_text == '{"name": "Alice"}'
    assert ("Content-Type", "application/json") in request.headers


def test_parse_data_implies_post() -> None:
    assert parse_curl("curl https://x.test -d '{}'").method == "POST"


def test_parse_basic_auth() -> None:
    request = parse_curl("curl -u alice:secret https://x.test")

    assert request.auth == ApiAuth(kind="basic", username="alice", password="secret")


def test_parse_bearer_header_becomes_auth() -> None:
    request = parse_curl("curl -H 'Authorization: Bearer abc' https://x.test")

    assert request.auth.kind == "bearer"
    assert request.auth.token == "abc"
    assert request.headers == []


def test_parse_form_urlencoded_data() -> None:
    request = parse_curl(
        "curl https://x.test -H 'Content-Type: application/x-www-form-urlencoded' -d 'a=1&b=2'"
    )

    assert request.body_kind == "form"
    assert request.form_fields == [("a", "1"), ("b", "2")]


def test_parse_head_flag() -> None:
    assert parse_curl("curl -I https://x.test").method == "HEAD"


def test_parse_ignores_unmodeled_flags() -> None:
    assert parse_curl("curl -s -L --compressed https://x.test").url == "https://x.test"


def test_parse_errors() -> None:
    with pytest.raises(CurlParseError):
        parse_curl("wget https://x.test")
    with pytest.raises(CurlParseError):
        parse_curl("curl -X POST")


def test_to_curl_round_trip() -> None:
    original = ApiRequest(
        method="POST",
        url="https://api.test/users",
        params=[("a", "1")],
        headers=[("X-Test", "y")],
        body_kind="json",
        body_text='{"n": 1}',
    )

    parsed = parse_curl(to_curl(original))

    assert parsed.method == "POST"
    assert parsed.url == "https://api.test/users"
    assert parsed.params == [("a", "1")]
    assert ("X-Test", "y") in parsed.headers
    assert parsed.body_text == '{"n": 1}'
