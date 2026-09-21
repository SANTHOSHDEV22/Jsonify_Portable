"""API request model shared by the API client, cURL, and code generators."""

from __future__ import annotations

import base64
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any
from urllib.parse import urlencode

SUPPORTED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

AUTH_KINDS = ("none", "basic", "bearer", "apikey", "custom")

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][\w.-]*)\s*\}\}")


@dataclass(slots=True)
class ApiAuth:
    """Authentication settings for a request."""

    kind: str = "none"  # none | basic | bearer | apikey | custom
    username: str = ""
    password: str = ""
    token: str = ""
    key_name: str = ""
    key_value: str = ""
    key_in: str = "header"  # header | query
    header_name: str = ""
    header_value: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiAuth:
        known = {item.name for item in fields(cls)}
        return cls(**{k: str(v) for k, v in data.items() if k in known})


@dataclass(slots=True)
class ApiRequest:
    """A fully described HTTP request (before variable substitution)."""

    method: str = "GET"
    url: str = ""
    params: list[tuple[str, str]] = field(default_factory=list)
    headers: list[tuple[str, str]] = field(default_factory=list)
    auth: ApiAuth = field(default_factory=ApiAuth)
    body_kind: str = "none"  # none | json | form
    body_text: str = ""
    form_fields: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "params": [list(pair) for pair in self.params],
            "headers": [list(pair) for pair in self.headers],
            "auth": self.auth.to_dict(),
            "body_kind": self.body_kind,
            "body_text": self.body_text,
            "form_fields": [list(pair) for pair in self.form_fields],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiRequest:
        def pairs(key: str) -> list[tuple[str, str]]:
            return [(str(p[0]), str(p[1])) for p in data.get(key, []) if len(p) == 2]

        auth_data = data.get("auth", {})
        return cls(
            method=str(data.get("method", "GET")),
            url=str(data.get("url", "")),
            params=pairs("params"),
            headers=pairs("headers"),
            auth=ApiAuth.from_dict(auth_data if isinstance(auth_data, dict) else {}),
            body_kind=str(data.get("body_kind", "none")),
            body_text=str(data.get("body_text", "")),
            form_fields=pairs("form_fields"),
        )


@dataclass(slots=True)
class EffectiveRequest:
    """What actually goes over the wire once auth/body defaults are applied."""

    method: str
    url: str
    params: list[tuple[str, str]]
    headers: list[tuple[str, str]]
    body: str | None


def apply_variables(request: ApiRequest, variables: dict[str, str]) -> ApiRequest:
    """Replace ``{{name}}`` placeholders with environment variable values.

    Unknown placeholders are left untouched so mistakes stay visible.
    """

    def substitute(text: str) -> str:
        return _VARIABLE_PATTERN.sub(lambda m: variables.get(m.group(1), m.group(0)), text)

    def walk(value: Any) -> Any:
        if isinstance(value, str):
            return substitute(value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        return value

    return ApiRequest.from_dict(walk(request.to_dict()))


def effective_request(request: ApiRequest) -> EffectiveRequest:
    """Resolve auth and body into the final URL/params/headers/body."""

    params = [(k, v) for k, v in request.params if k.strip()]
    headers = [(k, v) for k, v in request.headers if k.strip()]
    header_names = {name.lower() for name, _ in headers}
    auth = request.auth

    def add_header(name: str, value: str) -> None:
        if name.lower() not in header_names:
            headers.append((name, value))
            header_names.add(name.lower())

    if auth.kind == "basic":
        raw = f"{auth.username}:{auth.password}".encode()
        add_header("Authorization", "Basic " + base64.b64encode(raw).decode("ascii"))
    elif auth.kind == "bearer" and auth.token:
        add_header("Authorization", f"Bearer {auth.token}")
    elif auth.kind == "apikey" and auth.key_name:
        if auth.key_in == "query":
            params.append((auth.key_name, auth.key_value))
        else:
            add_header(auth.key_name, auth.key_value)
    elif auth.kind == "custom" and auth.header_name:
        add_header(auth.header_name, auth.header_value)

    body: str | None = None
    if request.body_kind == "json" and request.body_text.strip():
        body = request.body_text
        add_header("Content-Type", "application/json")
    elif request.body_kind == "form" and request.form_fields:
        body = urlencode([(k, v) for k, v in request.form_fields if k.strip()])
        add_header("Content-Type", "application/x-www-form-urlencoded")

    return EffectiveRequest(
        method=request.method.strip().upper(),
        url=request.url.strip(),
        params=params,
        headers=headers,
        body=body,
    )


def full_url(effective: EffectiveRequest) -> str:
    """Return the URL with query parameters appended."""

    if not effective.params:
        return effective.url

    separator = "&" if "?" in effective.url else "?"
    return f"{effective.url}{separator}{urlencode(effective.params)}"
