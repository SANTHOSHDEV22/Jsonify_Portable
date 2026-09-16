"""Shared type definitions for Jsonify."""

from __future__ import annotations

from typing import TypeAlias


JSONPrimitive: TypeAlias = str | int | float | bool | None

JSONValue: TypeAlias = (
    dict[str, "JSONValue"]
    | list["JSONValue"]
    | JSONPrimitive
)

JSONPathMatch: TypeAlias = tuple[str, JSONValue]