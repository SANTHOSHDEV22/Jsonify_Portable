"""Tests for JSON Pointer / JSONPath segment conversions."""

from __future__ import annotations

import pytest

from jsonify.core.pointer import from_json_pointer, to_json_path, to_json_pointer


def test_to_json_path_simple_object() -> None:
    assert to_json_path(["a", "b"]) == "$.a.b"


def test_to_json_path_with_array_index() -> None:
    assert to_json_path(["users", 0, "name"]) == "$.users[0].name"


def test_to_json_path_non_identifier_key() -> None:
    assert to_json_path(["a-b"]) == "$['a-b']"


def test_to_json_path_empty_segments() -> None:
    assert to_json_path([]) == "$"


def test_to_json_pointer_simple() -> None:
    assert to_json_pointer(["a", "b"]) == "/a/b"


def test_to_json_pointer_with_index() -> None:
    assert to_json_pointer(["users", 0, "name"]) == "/users/0/name"


def test_to_json_pointer_escapes_special_chars() -> None:
    assert to_json_pointer(["a/b", "c~d"]) == "/a~1b/c~0d"


def test_to_json_pointer_empty_segments() -> None:
    assert to_json_pointer([]) == ""


def test_from_json_pointer_round_trip() -> None:
    segments = ["users", 0, "name"]
    pointer = to_json_pointer(segments)
    assert from_json_pointer(pointer) == segments


def test_from_json_pointer_unescapes() -> None:
    assert from_json_pointer("/a~1b/c~0d") == ["a/b", "c~d"]


def test_from_json_pointer_empty() -> None:
    assert from_json_pointer("") == []
    assert from_json_pointer("/") == []


def test_from_json_pointer_requires_leading_slash() -> None:
    with pytest.raises(ValueError):
        from_json_pointer("a/b")
