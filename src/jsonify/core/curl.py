"""cURL command import and export."""

from __future__ import annotations

import re
import shlex
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from jsonify.core.api_request import ApiAuth, ApiRequest, effective_request, full_url


class CurlParseError(ValueError):
    """Raised when a cURL command can't be understood."""


_DATA_FLAGS = {"-d", "--data", "--data-raw", "--data-binary", "--data-ascii", "--data-urlencode"}
_FORM_FLAGS = {"-F", "--form"}
_VALUE_FLAGS_TO_SKIP = {"-o", "--output", "-A", "--user-agent", "-e", "--referer", "-b", "--cookie"}


def parse_curl(command: str) -> ApiRequest:
    """Convert a pasted ``curl`` command into an :class:`ApiRequest`."""

    cleaned = re.sub(r"\\\r?\n", " ", command.strip())
    cleaned = re.sub(r"\^\r?\n", " ", cleaned)

    try:
        tokens = shlex.split(cleaned, posix=True)
    except ValueError as error:
        raise CurlParseError(f"Could not parse the command: {error}") from error

    if not tokens or tokens[0].lower() != "curl":
        raise CurlParseError("The command must start with 'curl'.")

    method: str | None = None
    url = ""
    headers: list[tuple[str, str]] = []
    data_parts: list[str] = []
    form_fields: list[tuple[str, str]] = []
    auth = ApiAuth()
    head_only = False

    remaining = iter(tokens[1:])

    def take(flag: str) -> str:
        value = next(remaining, None)
        if value is None:
            raise CurlParseError(f"Missing value after {flag}.")
        return value

    for token in remaining:
        if token in ("-X", "--request"):
            method = take(token).upper()
        elif token in ("-H", "--header"):
            name, _, header_value = take(token).partition(":")
            headers.append((name.strip(), header_value.strip()))
        elif token in _DATA_FLAGS:
            data_parts.append(take(token))
        elif token in _FORM_FLAGS:
            name, _, form_value = take(token).partition("=")
            form_fields.append((name, form_value))
        elif token in ("-u", "--user"):
            username, _, password = take(token).partition(":")
            auth = ApiAuth(kind="basic", username=username, password=password)
        elif token in ("-I", "--head"):
            head_only = True
        elif token == "--url":
            url = take(token)
        elif token.startswith("-"):
            # Flags we don't model (e.g. -s, -L, -k, --compressed) are ignored;
            # a few take a value that must be skipped too.
            if token in _VALUE_FLAGS_TO_SKIP:
                take(token)
        elif not url:
            url = token

    if not url:
        raise CurlParseError("No URL found in the cURL command.")

    split = urlsplit(url)
    params = parse_qsl(split.query, keep_blank_values=True)
    base_url = urlunsplit((split.scheme, split.netloc, split.path, "", split.fragment))

    # Promote "Authorization: Bearer ..." to structured auth.
    remaining_headers: list[tuple[str, str]] = []
    for name, header_value in headers:
        if name.lower() == "authorization" and header_value.lower().startswith("bearer "):
            auth = ApiAuth(kind="bearer", token=header_value[7:].strip())
        else:
            remaining_headers.append((name, header_value))

    body_kind = "none"
    body_text = ""
    if form_fields:
        body_kind = "form"
    elif data_parts:
        body_text = "&".join(data_parts) if len(data_parts) > 1 else data_parts[0]
        content_type = next(
            (v.lower() for n, v in remaining_headers if n.lower() == "content-type"), ""
        )
        if "x-www-form-urlencoded" in content_type and not body_text.lstrip().startswith(
            ("{", "[")
        ):
            form_fields = parse_qsl(body_text, keep_blank_values=True)
            body_kind, body_text = "form", ""
        else:
            body_kind = "json"

    if method is None:
        method = "HEAD" if head_only else ("POST" if body_kind != "none" else "GET")

    return ApiRequest(
        method=method,
        url=base_url,
        params=params,
        headers=remaining_headers,
        auth=auth,
        body_kind=body_kind,
        body_text=body_text,
        form_fields=form_fields,
    )


def to_curl(request: ApiRequest) -> str:
    """Render a request as a multi-line ``curl`` command."""

    effective = effective_request(request)
    lines = [f"curl -X {effective.method} {shlex.quote(full_url(effective))}"]

    for name, value in effective.headers:
        lines.append(f"-H {shlex.quote(f'{name}: {value}')}")

    if effective.body is not None:
        lines.append(f"--data-raw {shlex.quote(effective.body)}")

    return " \\\n  ".join(lines)
