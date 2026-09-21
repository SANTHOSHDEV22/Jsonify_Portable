"""Tests for portable mode, diagnostics, plugins, sessions and update checks."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from jsonify.core import app_paths
from jsonify.core.diagnostics import deep_size, measure_document
from jsonify.core.plugins import PluginRegistry
from jsonify.core.session import SessionWorkspace
from jsonify.services.session_service import SessionService
from jsonify.services.update_service import (
    UpdateCheckError,
    UpdateService,
    is_newer,
    parse_version,
)

# ---------------------------------------------------------------- app paths


def test_data_dir_defaults_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(app_paths.PORTABLE_ENV, raising=False)
    monkeypatch.delenv(app_paths.DATA_DIR_ENV, raising=False)
    monkeypatch.setattr(app_paths, "app_root", lambda: Path("/nonexistent-root"))

    assert app_paths.data_dir() == Path.home() / ".jsonify"
    assert not app_paths.is_portable()


def test_portable_env_uses_data_folder_next_to_app(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(app_paths.DATA_DIR_ENV, raising=False)
    monkeypatch.setenv(app_paths.PORTABLE_ENV, "1")
    monkeypatch.setattr(app_paths, "app_root", lambda: tmp_path)

    assert app_paths.is_portable()
    assert app_paths.data_dir() == tmp_path / "data"


def test_portable_flag_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(app_paths.PORTABLE_ENV, raising=False)
    monkeypatch.delenv(app_paths.DATA_DIR_ENV, raising=False)
    monkeypatch.setattr(app_paths, "app_root", lambda: tmp_path)
    (tmp_path / app_paths.PORTABLE_FLAG_FILE).write_text("", encoding="utf-8")

    assert app_paths.is_portable()


def test_data_dir_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(app_paths.DATA_DIR_ENV, str(tmp_path / "custom"))

    assert app_paths.data_dir() == tmp_path / "custom"


# -------------------------------------------------------------- diagnostics


def test_measure_document_reports_structure() -> None:
    text = json.dumps({"a": [1, 2, {"b": None}], "c": "x"})

    report, value = measure_document(text)

    assert value == json.loads(text)
    assert report.size_bytes == len(text)
    assert report.node_count == 7
    assert report.max_depth == 3
    assert report.parse_ms >= 0
    assert report.deep_size_bytes > 0
    assert "Parse time" in report.format()


def test_measure_document_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        measure_document("{")


def test_deep_size_grows_with_content() -> None:
    assert deep_size({"a": list(range(1000))}) > deep_size({"a": [1]})


# ------------------------------------------------------------------ plugins


def test_register_and_use_plugin_features() -> None:
    registry = PluginRegistry()
    registry.register_converter("Upper", from_json=lambda value: json.dumps(value).upper())
    registry.register_analyzer("Has a", lambda payload: ["found a"] if "a" in payload else [])
    registry.register_tool("Reverse", lambda text: text[::-1])

    assert registry.converters["Upper"].from_json({"a": 1}) == '{"A": 1}'
    assert registry.run_analyzers({"a": 1}) == {"Has a": ["found a"]}
    assert registry.run_analyzers({"b": 1}) == {}
    assert registry.tools["Reverse"]("abc") == "cba"


def test_converter_needs_a_direction() -> None:
    with pytest.raises(ValueError):
        PluginRegistry().register_converter("Nothing")


def test_failing_analyzer_is_contained() -> None:
    registry = PluginRegistry()
    registry.register_analyzer("Boom", lambda payload: 1 / 0)

    assert "Analyzer failed" in registry.run_analyzers({})["Boom"][0]


def test_load_plugin_directory(tmp_path: Path) -> None:
    (tmp_path / "good.py").write_text(
        "def register(registry):\n    registry.register_tool('Shout', lambda text: text.upper())\n",
        encoding="utf-8",
    )
    (tmp_path / "broken.py").write_text("raise RuntimeError('nope')\n", encoding="utf-8")
    (tmp_path / "no_register.py").write_text("x = 1\n", encoding="utf-8")

    registry = PluginRegistry()
    registry.load(tmp_path)
    registry.load(tmp_path)  # idempotent

    assert registry.tools["Shout"]("a") == "A"
    assert registry.loaded == ["file 'good.py'"]
    assert len(registry.errors) == 4  # broken + no_register, reported on both loads


# ----------------------------------------------------- bookmarks/annotations


def test_session_round_trips_bookmarks_and_annotations(tmp_path: Path) -> None:
    service = SessionService()
    session = service.create_session(
        name="s",
        payload={"a": 1},
        bookmarks=["/a"],
        annotations={"/a": "important"},
    )

    path = service.save(session, tmp_path / "s.jsonify")
    loaded = service.load(path)

    assert loaded.workspace.bookmarks == ["/a"]
    assert loaded.workspace.annotations == {"/a": "important"}


def test_old_sessions_without_notes_still_load() -> None:
    workspace = SessionWorkspace.from_dict({"selected_tab": "json:Graph"})

    assert workspace.bookmarks == []
    assert workspace.annotations == {}


def test_malformed_notes_are_ignored() -> None:
    workspace = SessionWorkspace.from_dict({"bookmarks": "oops", "annotations": [1, 2]})

    assert workspace.bookmarks == []
    assert workspace.annotations == {}


# ------------------------------------------------------------------ updates


def test_version_parsing_and_comparison() -> None:
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.10.0-beta.1") == (1, 10, 0)
    assert is_newer("1.10.0", "1.9.9")
    assert is_newer("v2.0", "1.9.9")
    assert not is_newer("1.0.0", "1.0.0")
    assert not is_newer("1.0", "1.0.0")
    assert not is_newer("0.9.9", "1.0.0")


def _update_service(status: int, body: object) -> UpdateService:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/releases/latest" in str(request.url)
        return httpx.Response(status, json=body)

    return UpdateService("owner/repo", transport=httpx.MockTransport(handler))


def test_update_available() -> None:
    service = _update_service(
        200, {"tag_name": "v1.2.0", "html_url": "https://example.test/r", "body": "notes"}
    )

    info = service.check("1.0.0")

    assert info.is_newer
    assert info.latest_version == "1.2.0"
    assert info.release_url == "https://example.test/r"


def test_up_to_date() -> None:
    assert not _update_service(200, {"tag_name": "v1.0.0"}).check("1.0.0").is_newer


def test_no_releases_published() -> None:
    with pytest.raises(UpdateCheckError, match="No releases"):
        _update_service(404, {}).check("1.0.0")


def test_bad_responses() -> None:
    with pytest.raises(UpdateCheckError):
        _update_service(500, {}).check("1.0.0")
    with pytest.raises(UpdateCheckError):
        _update_service(200, {"unexpected": True}).check("1.0.0")


def test_network_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    service = UpdateService("owner/repo", transport=httpx.MockTransport(handler))

    with pytest.raises(UpdateCheckError, match="Could not reach"):
        service.check("1.0.0")
