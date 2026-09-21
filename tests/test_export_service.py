"""Tests for the Jsonify export service."""

from __future__ import annotations

import json
from pathlib import Path

from jsonify.services.export_service import (
    ExportService,
)


def test_export_json(
    tmp_path: Path,
) -> None:
    service = ExportService()

    payload = {
        "id": 1,
        "name": "Alice",
        "active": True,
    }

    result = service.export_json(
        payload,
        tmp_path / "payload.json",
    )

    assert result.exists()

    loaded = json.loads(result.read_text(encoding="utf-8"))

    assert loaded == payload


def test_json_extension_added(
    tmp_path: Path,
) -> None:
    service = ExportService()

    result = service.export_json(
        {"id": 1},
        tmp_path / "payload",
    )

    assert result.suffix == ".json"
    assert result.exists()


def test_export_nested_json(
    tmp_path: Path,
) -> None:
    service = ExportService()

    payload = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
            },
            {
                "id": 2,
                "name": "Bob",
            },
        ]
    }

    result = service.export_json(
        payload,
        tmp_path / "users.json",
    )

    loaded = json.loads(result.read_text(encoding="utf-8"))

    assert loaded == payload


def test_unicode_preserved(
    tmp_path: Path,
) -> None:
    service = ExportService()

    payload = {
        "message": "வணக்கம்",
    }

    result = service.export_json(
        payload,
        tmp_path / "unicode.json",
    )

    text = result.read_text(encoding="utf-8")

    assert "வணக்கம்" in text


def test_export_text(
    tmp_path: Path,
) -> None:
    service = ExportService()

    result = service.export_text(
        "<svg></svg>",
        tmp_path / "graph.svg",
        extension=".svg",
    )

    assert result.exists()

    assert result.read_text(encoding="utf-8") == "<svg></svg>"


def test_text_extension_added(
    tmp_path: Path,
) -> None:
    service = ExportService()

    result = service.export_text(
        "test",
        tmp_path / "graph",
        extension="svg",
    )

    assert result.suffix == ".svg"


def test_json_null(
    tmp_path: Path,
) -> None:
    service = ExportService()

    result = service.export_json(
        None,
        tmp_path / "null.json",
    )

    assert result.read_text(encoding="utf-8") == "null"


def test_json_array(
    tmp_path: Path,
) -> None:
    service = ExportService()

    payload = [
        1,
        2,
        3,
    ]

    result = service.export_json(
        payload,
        tmp_path / "array.json",
    )

    loaded = json.loads(result.read_text(encoding="utf-8"))

    assert loaded == payload
