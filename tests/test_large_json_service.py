"""Tests for LargeJsonService."""

from __future__ import annotations

from jsonify.services.large_json_service import (
    LargeJsonService,
    LargeJsonSettings,
)


def test_small_json_not_lazy() -> None:
    service = LargeJsonService(
        LargeJsonSettings(
            lazy_threshold=10,
        )
    )

    info = service.analyze(
        {
            "id": 1,
            "name": "Alice",
        }
    )

    assert service.should_use_lazy_tree(info) is False


def test_large_json_uses_lazy_tree() -> None:
    service = LargeJsonService(
        LargeJsonSettings(
            lazy_threshold=10,
        )
    )

    payload = list(range(20))

    info = service.analyze(payload)

    assert service.should_use_lazy_tree(info) is True


def test_object_preview() -> None:
    service = LargeJsonService()

    assert (
        service.preview(
            {
                "id": 1,
                "name": "Alice",
            }
        )
        == "Object (2 properties)"
    )


def test_array_preview() -> None:
    service = LargeJsonService()

    assert service.preview([1, 2, 3]) == "Array (3 items)"


def test_long_string_preview() -> None:
    service = LargeJsonService(
        LargeJsonSettings(
            preview_length=5,
        )
    )

    result = service.preview("abcdefghij")

    assert result == "abcde..."


def test_boolean_preview() -> None:
    service = LargeJsonService()

    assert service.preview(True) == "true"


def test_null_preview() -> None:
    service = LargeJsonService()

    assert service.preview(None) == "null"
