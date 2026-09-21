"""Generate HTTP request code snippets from an :class:`ApiRequest`."""

from __future__ import annotations

import json

from jsonify.core.api_request import ApiRequest, effective_request, full_url

SUPPORTED_REQUEST_LANGUAGES = ("python", "javascript", "csharp", "java")


def generate_request_code(request: ApiRequest, language: str) -> str:
    """Render ``request`` as a runnable example in ``language``."""

    generators = {
        "python": _python,
        "javascript": _javascript,
        "csharp": _csharp,
        "java": _java,
    }

    if language not in generators:
        raise ValueError(f"Unsupported request code language: {language!r}")

    return generators[language](request)


def _python(request: ApiRequest) -> str:
    eff = effective_request(request)
    lines = ["import requests", "", f"url = {json.dumps(eff.url)}"]

    if eff.params:
        lines.append(f"params = {json.dumps(dict(eff.params), indent=4)}")
    if eff.headers:
        lines.append(f"headers = {json.dumps(dict(eff.headers), indent=4)}")
    if eff.body is not None:
        lines.append(f"data = {json.dumps(eff.body)}")

    args = ["url"]
    if eff.params:
        args.append("params=params")
    if eff.headers:
        args.append("headers=headers")
    if eff.body is not None:
        args.append("data=data")

    lines += ["", f"response = requests.request({json.dumps(eff.method)}, {', '.join(args)})"]
    lines.append("print(response.status_code)")
    lines.append("print(response.text)")
    return "\n".join(lines)


def _javascript(request: ApiRequest) -> str:
    eff = effective_request(request)
    options = [f"  method: {json.dumps(eff.method)},"]

    if eff.headers:
        headers = json.dumps(dict(eff.headers), indent=4).replace("\n", "\n  ")
        options.append(f"  headers: {headers},")
    if eff.body is not None:
        options.append(f"  body: {json.dumps(eff.body)},")

    return (
        f"const response = await fetch({json.dumps(full_url(eff))}, {{\n"
        + "\n".join(options)
        + "\n});\n\nconsole.log(response.status);\nconsole.log(await response.text());"
    )


def _csharp(request: ApiRequest) -> str:
    eff = effective_request(request)
    lines = [
        "using var client = new HttpClient();",
        f"var request = new HttpRequestMessage(new HttpMethod({json.dumps(eff.method)}), "
        f"{json.dumps(full_url(eff))});",
    ]

    for name, value in eff.headers:
        if name.lower() == "content-type":
            continue
        lines.append(
            f"request.Headers.TryAddWithoutValidation({json.dumps(name)}, {json.dumps(value)});"
        )

    if eff.body is not None:
        content_type = next(
            (v for n, v in eff.headers if n.lower() == "content-type"), "text/plain"
        )
        lines.append(
            f"request.Content = new StringContent({json.dumps(eff.body)}, "
            f"System.Text.Encoding.UTF8, {json.dumps(content_type)});"
        )

    lines += [
        "",
        "var response = await client.SendAsync(request);",
        "Console.WriteLine((int)response.StatusCode);",
        "Console.WriteLine(await response.Content.ReadAsStringAsync());",
    ]
    return "\n".join(lines)


def _java(request: ApiRequest) -> str:
    eff = effective_request(request)
    publisher = (
        f"HttpRequest.BodyPublishers.ofString({json.dumps(eff.body)})"
        if eff.body is not None
        else "HttpRequest.BodyPublishers.noBody()"
    )

    lines = [
        "HttpClient client = HttpClient.newHttpClient();",
        "HttpRequest request = HttpRequest.newBuilder()",
        f"    .uri(URI.create({json.dumps(full_url(eff))}))",
    ]
    for name, value in eff.headers:
        lines.append(f"    .header({json.dumps(name)}, {json.dumps(value)})")
    lines += [
        f"    .method({json.dumps(eff.method)}, {publisher})",
        "    .build();",
        "",
        "HttpResponse<String> response =",
        "    client.send(request, HttpResponse.BodyHandlers.ofString());",
        "System.out.println(response.statusCode());",
        "System.out.println(response.body());",
    ]
    return "\n".join(lines)
