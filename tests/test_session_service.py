"""Tests for Jsonify saved sessions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jsonify.services.session_service import (
    SessionError,
    SessionService,
)


def test_create_session() -> None:
    service = SessionService()

    payload = {
        "name": "Alice",
    }

    session = service.create_session(
        name="Test Session",
        payload=payload,
        selected_tab="JSONPath",
        jsonpath_query="$.users[*].name",
    )

    assert session.name == "Test Session"
    assert session.payload == payload

    assert (
        session.workspace.selected_tab
        == "JSONPath"
    )

    assert (
        session.workspace.jsonpath_query
        == "$.users[*].name"
    )


def test_empty_name_becomes_untitled() -> None:
    service = SessionService()

    session = service.create_session(
        name="   ",
        payload={},
    )

    assert (
        session.name
        == "Untitled Session"
    )


def test_save_session(
    tmp_path: Path,
) -> None:
    service = SessionService()

    session = service.create_session(
        name="Test",
        payload={
            "id": 1,
        },
    )

    file_path = tmp_path / "test.jsonify"

    result = service.save(
        session,
        file_path,
    )

    assert result.exists()

    data = json.loads(
        result.read_text(
            encoding="utf-8"
        )
    )

    assert (
        data["format"]
        == "jsonify-session"
    )

    assert data["version"] == 1
    assert data["name"] == "Test"
    assert data["payload"] == {"id": 1}


def test_extension_is_added(
    tmp_path: Path,
) -> None:
    service = SessionService()

    session = service.create_session(
        name="Test",
        payload={},
    )

    result = service.save(
        session,
        tmp_path / "test",
    )

    assert (
        result.suffix
        == ".jsonify"
    )

    assert result.exists()


def test_load_session(
    tmp_path: Path,
) -> None:
    service = SessionService()

    original = service.create_session(
        name="API Debugging",
        payload={
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                }
            ]
        },
        selected_tab="JSONPath",
        jsonpath_query="$.users[*].name",
    )

    file_path = service.save(
        original,
        tmp_path / "api.jsonify",
    )

    loaded = service.load(
        file_path
    )

    assert (
        loaded.name
        == "API Debugging"
    )

    assert (
        loaded.payload
        == original.payload
    )

    assert (
        loaded.workspace.selected_tab
        == "JSONPath"
    )

    assert (
        loaded.workspace.jsonpath_query
        == "$.users[*].name"
    )


def test_invalid_json_file(
    tmp_path: Path,
) -> None:
    service = SessionService()

    file_path = (
        tmp_path
        / "broken.jsonify"
    )

    file_path.write_text(
        "not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        SessionError
    ):
        service.load(
            file_path
        )


def test_wrong_file_format(
    tmp_path: Path,
) -> None:
    service = SessionService()

    file_path = (
        tmp_path
        / "wrong.jsonify"
    )

    file_path.write_text(
        json.dumps(
            {
                "format": "something-else",
                "version": 1,
                "payload": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        SessionError,
        match="not a Jsonify session",
    ):
        service.load(
            file_path
        )


def test_unsupported_version(
    tmp_path: Path,
) -> None:
    service = SessionService()

    file_path = (
        tmp_path
        / "future.jsonify"
    )

    file_path.write_text(
        json.dumps(
            {
                "format": "jsonify-session",
                "version": 999,
                "payload": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        SessionError,
        match="Unsupported",
    ):
        service.load(
            file_path
        )


def test_missing_payload(
    tmp_path: Path,
) -> None:
    service = SessionService()

    file_path = (
        tmp_path
        / "missing.jsonify"
    )

    file_path.write_text(
        json.dumps(
            {
                "format": "jsonify-session",
                "version": 1,
                "name": "Broken",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        SessionError,
        match="payload",
    ):
        service.load(
            file_path
        )


def test_original_payload_preserved(
    tmp_path: Path,
) -> None:
    service = SessionService()

    payload = {
        "users": [
            {
                "id": 1,
                "active": True,
                "value": None,
            }
        ]
    }

    session = service.create_session(
        name="Test",
        payload=payload,
    )

    file_path = service.save(
        session,
        tmp_path / "test.jsonify",
    )

    loaded = service.load(
        file_path
    )

    assert loaded.payload == payload