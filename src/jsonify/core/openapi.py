"""Extract a response JSON Schema from an OpenAPI document.

Supports OpenAPI 3.x documents (JSON or already-parsed dict) and resolves
local ``#/...`` ``$ref`` pointers so the returned schema is self-contained
and can be handed straight to a JSON Schema validator.
"""

from __future__ import annotations

from typing import Any

_MAX_REF_DEPTH = 20


class OpenApiError(ValueError):
    """Raised when a response schema can't be located in an OpenAPI document."""


def extract_response_schema(
    openapi_doc: dict[str, Any],
    *,
    path: str,
    method: str,
    status: str = "200",
) -> dict[str, Any]:
    """Return the (ref-resolved) JSON Schema for one operation's response body."""

    paths = openapi_doc.get("paths", {})
    path_item = paths.get(path)
    if path_item is None:
        raise OpenApiError(f"Path not found in OpenAPI document: {path}")

    operation = path_item.get(method.lower())
    if operation is None:
        raise OpenApiError(f"Method {method.upper()} not defined for path: {path}")

    responses = operation.get("responses", {})
    response = responses.get(str(status)) or responses.get("default")
    if response is None:
        raise OpenApiError(f"No response defined for status {status} on {method.upper()} {path}.")

    content = response.get("content", {})
    json_content = content.get("application/json")
    if json_content is None:
        raise OpenApiError(
            f"No application/json response body defined for {method.upper()} {path}."
        )

    schema = json_content.get("schema")
    if schema is None:
        raise OpenApiError(f"Response has no schema for {method.upper()} {path}.")

    return _resolve_refs(schema, openapi_doc)


def list_operations(openapi_doc: dict[str, Any]) -> list[tuple[str, str]]:
    """List every (path, method) operation defined in the document."""

    operations: list[tuple[str, str]] = []
    for path, path_item in openapi_doc.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if method in path_item:
                operations.append((path, method))
    return operations


def _resolve_refs(node: Any, doc: dict[str, Any], *, depth: int = 0) -> Any:
    if depth > _MAX_REF_DEPTH:
        return node

    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            target = _resolve_pointer(doc, ref)
            if target is None:
                return node
            return _resolve_refs(target, doc, depth=depth + 1)

        return {key: _resolve_refs(value, doc, depth=depth + 1) for key, value in node.items()}

    if isinstance(node, list):
        return [_resolve_refs(item, doc, depth=depth + 1) for item in node]

    return node


def _resolve_pointer(doc: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        raise OpenApiError(f"Only local '#/...' $refs are supported, got: {ref}")

    node: Any = doc
    for raw_segment in ref[2:].split("/"):
        segment = raw_segment.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and segment in node:
            node = node[segment]
        else:
            return None

    return node
