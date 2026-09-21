"""Tests for the API request model."""

from __future__ import annotations

import base64

from jsonify.core.api_request import (
    ApiAuth,
    ApiRequest,
    apply_variables,
    effective_request,
    full_url,
)


def test_round_trip_dict() -> None:
    request = ApiRequest(
        method="POST",
        url="https://x.test/a",
        params=[("a", "1")],
        headers=[("X-Test", "y")],
        auth=ApiAuth(kind="bearer", token="t"),
        body_kind="json",
        body_text="{}",
    )

    assert ApiRequest.from_dict(request.to_dict()) == request


def test_apply_variables_replaces_known_and_keeps_unknown() -> None:
    request = ApiRequest(
        url="{{base_url}}/users",
        headers=[("Authorization", "Bearer {{token}}")],
        params=[("q", "{{missing}}")],
    )

    result = apply_variables(request, {"base_url": "https://dev.test", "token": "abc"})

    assert result.url == "https://dev.test/users"
    assert result.headers == [("Authorization", "Bearer abc")]
    assert result.params == [("q", "{{missing}}")]


def test_effective_basic_auth_header() -> None:
    request = ApiRequest(
        url="https://x.test", auth=ApiAuth(kind="basic", username="u", password="p")
    )

    headers = dict(effective_request(request).headers)

    assert headers["Authorization"] == "Basic " + base64.b64encode(b"u:p").decode()


def test_effective_bearer_auth_header() -> None:
    request = ApiRequest(url="https://x.test", auth=ApiAuth(kind="bearer", token="abc"))

    assert dict(effective_request(request).headers)["Authorization"] == "Bearer abc"


def test_effective_api_key_in_header_and_query() -> None:
    header_req = ApiRequest(
        url="https://x.test", auth=ApiAuth(kind="apikey", key_name="X-Key", key_value="v")
    )
    query_req = ApiRequest(
        url="https://x.test",
        auth=ApiAuth(kind="apikey", key_name="key", key_value="v", key_in="query"),
    )

    assert dict(effective_request(header_req).headers)["X-Key"] == "v"
    assert ("key", "v") in effective_request(query_req).params


def test_effective_custom_header_auth() -> None:
    request = ApiRequest(
        url="https://x.test", auth=ApiAuth(kind="custom", header_name="X-Auth", header_value="z")
    )

    assert dict(effective_request(request).headers)["X-Auth"] == "z"


def test_explicit_header_wins_over_auth() -> None:
    request = ApiRequest(
        url="https://x.test",
        headers=[("authorization", "Custom")],
        auth=ApiAuth(kind="bearer", token="abc"),
    )

    assert dict(effective_request(request).headers)["authorization"] == "Custom"


def test_form_body_is_urlencoded() -> None:
    request = ApiRequest(
        method="POST",
        url="https://x.test",
        body_kind="form",
        form_fields=[("a", "1 2"), ("b", "x")],
    )

    effective = effective_request(request)

    assert effective.body == "a=1+2&b=x"
    assert dict(effective.headers)["Content-Type"] == "application/x-www-form-urlencoded"


def test_full_url_appends_params() -> None:
    effective = effective_request(ApiRequest(url="https://x.test/a", params=[("q", "1")]))

    assert full_url(effective) == "https://x.test/a?q=1"
