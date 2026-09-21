"""A small, pure-Python subset of jq.

This is deliberately **not** a full jq implementation — it covers the
filters people reach for day to day, without requiring a native ``libjq``
binary or C extension, so Jsonify stays simple to package on every
platform.

Supported syntax:
    - ``.``                     identity
    - ``.a.b.c``                field access
    - ``.a[0]``                 array index
    - ``.a[]`` / ``.[]``        iterate an array's items or an object's values
    - ``keys``                  sorted object keys
    - ``length``                length of an array/object/string, or abs(number)
    - ``select(.a == 1)``       filter (supports ==, !=, <, >, <=, >=, or a bare
                                 truthy field check), on the current item
    - ``map(.a)``                apply a field path to every item of an array
    - ``a | b | c``             pipe stages together

Each stage after a ``|`` runs against every value produced by the
previous stage, so ``.users[] | select(.active == true) | .name`` reads
the same way it does in real jq.
"""

from __future__ import annotations

import json
from typing import Any

from jsonify.core.models import JSONValue

PathSegment = tuple[str, str | int]

_COMPARISON_OPERATORS = ("==", "!=", ">=", "<=", ">", "<")


class JqQueryError(ValueError):
    """Raised when a jq-lite query is malformed or uses unsupported syntax."""


def run_jq(data: JSONValue, query: str) -> list[JSONValue]:
    """Run a jq-lite query against ``data`` and return every result."""

    query = query.strip()
    if not query:
        raise JqQueryError("jq query cannot be empty.")

    results: list[JSONValue] = [data]

    for stage in _split_pipeline(query):
        next_results: list[JSONValue] = []
        for item in results:
            next_results.extend(_apply_stage(item, stage))
        results = next_results

    return results


# ---------------------------------------------------------------------
# Pipeline splitting
# ---------------------------------------------------------------------


def _split_pipeline(query: str) -> list[str]:
    stages: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False

    for char in query:
        if in_string:
            current.append(char)
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            current.append(char)
            continue

        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1

        if char == "|" and depth == 0:
            stages.append("".join(current))
            current = []
            continue

        current.append(char)

    stages.append("".join(current))

    if in_string:
        raise JqQueryError("Unterminated string in jq query.")
    if depth != 0:
        raise JqQueryError("Unbalanced parentheses/brackets in jq query.")

    stripped = [stage.strip() for stage in stages]
    if not stripped or not stripped[0]:
        raise JqQueryError("jq query cannot be empty.")

    return stripped


# ---------------------------------------------------------------------
# Path tokenizing (".a.b[0][]")
# ---------------------------------------------------------------------


def _tokenize_path(path: str) -> list[PathSegment]:
    if not path.startswith("."):
        raise JqQueryError(f"Expected a path starting with '.', got: {path!r}")

    tokens: list[PathSegment] = []
    i = 1
    n = len(path)

    while i < n:
        char = path[i]

        if char == ".":
            i += 1
            continue

        if char == "[":
            end = path.find("]", i)
            if end == -1:
                raise JqQueryError(f"Unterminated '[' in path: {path!r}")

            inner = path[i + 1 : end]

            if inner == "":
                tokens.append(("iterate", ""))
            elif inner.lstrip("-").isdigit():
                tokens.append(("index", int(inner)))
            else:
                raise JqQueryError(f"Unsupported index expression: [{inner}]")

            i = end + 1
            continue

        j = i
        while j < n and path[j] not in ".[":
            j += 1

        ident = path[i:j]
        if not ident:
            raise JqQueryError(f"Invalid path near: {path[i:]!r}")

        tokens.append(("field", ident))
        i = j

    return tokens


def _fan_out_path(value: JSONValue, tokens: list[PathSegment]) -> list[JSONValue]:
    """Apply a path, fanning out at every ``[]`` (iterate) step."""

    current: list[JSONValue] = [value]

    for kind, arg in tokens:
        next_current: list[JSONValue] = []

        for item in current:
            if kind == "field":
                next_current.append(item.get(str(arg)) if isinstance(item, dict) else None)
            elif kind == "index":
                if (
                    isinstance(item, list)
                    and isinstance(arg, int)
                    and -len(item) <= arg < len(item)
                ):
                    next_current.append(item[arg])
                else:
                    next_current.append(None)
            elif kind == "iterate":
                if isinstance(item, list):
                    next_current.extend(item)
                elif isinstance(item, dict):
                    next_current.extend(item.values())
                # Non-container values under `[]` produce nothing.

        current = next_current

    return current


def _resolve_single_path(value: JSONValue, tokens: list[PathSegment]) -> JSONValue:
    """Apply a path with no fan-out (used inside select()/map())."""

    current = value

    for kind, arg in tokens:
        if kind == "field":
            current = current.get(str(arg)) if isinstance(current, dict) else None
        elif kind == "index":
            if (
                isinstance(current, list)
                and isinstance(arg, int)
                and -len(current) <= arg < len(current)
            ):
                current = current[arg]
            else:
                current = None
        elif kind == "iterate":
            raise JqQueryError("select()/map() expressions cannot use '[]' iteration.")

    return current


# ---------------------------------------------------------------------
# Stage evaluation
# ---------------------------------------------------------------------


def _apply_stage(value: JSONValue, stage: str) -> list[JSONValue]:
    if stage == ".":
        return [value]

    if stage == "keys":
        if not isinstance(value, dict):
            raise JqQueryError("keys expects an object.")
        return [list(sorted(value.keys()))]

    if stage == "length":
        return [_jq_length(value)]

    if stage.startswith("select(") and stage.endswith(")"):
        expr = stage[len("select(") : -1]
        return [value] if _evaluate_select(value, expr) else []

    if stage.startswith("map(") and stage.endswith(")"):
        inner = stage[len("map(") : -1].strip()
        if not isinstance(value, list):
            raise JqQueryError("map() expects an array.")
        tokens = _tokenize_path(inner) if inner != "." else []
        mapped = [_resolve_single_path(item, tokens) if tokens else item for item in value]
        return [mapped]

    if stage.startswith("."):
        return _fan_out_path(value, _tokenize_path(stage))

    raise JqQueryError(f"Unsupported jq expression: {stage!r}")


def _jq_length(value: JSONValue) -> int | float:
    if value is None:
        return 0
    if isinstance(value, bool):
        raise JqQueryError("length is not defined for booleans.")
    if isinstance(value, dict | list | str):
        return len(value)
    if isinstance(value, int | float):
        return abs(value)
    raise JqQueryError("length is not supported for this value.")


def _evaluate_select(value: JSONValue, expr: str) -> bool:
    expr = expr.strip()

    for operator in _COMPARISON_OPERATORS:
        if operator in expr:
            left_text, right_text = expr.split(operator, 1)
            left_value = _resolve_single_path(value, _tokenize_path(left_text.strip()))

            try:
                right_value = json.loads(right_text.strip())
            except json.JSONDecodeError as error:
                raise JqQueryError(
                    f"Invalid literal in select(): {right_text.strip()!r}"
                ) from error

            return _compare(left_value, operator, right_value)

    result = _resolve_single_path(value, _tokenize_path(expr))
    return result is not None and result is not False


def _compare(left: Any, operator: str, right: Any) -> bool:
    try:
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator == ">":
            return left > right
        if operator == "<":
            return left < right
        if operator == ">=":
            return left >= right
        if operator == "<=":
            return left <= right
    except TypeError:
        return False

    return False
