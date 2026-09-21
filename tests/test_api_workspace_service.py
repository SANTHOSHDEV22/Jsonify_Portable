"""Tests for API history / collections / environments persistence."""

from __future__ import annotations

from pathlib import Path

from jsonify.core.api_request import ApiRequest
from jsonify.services.api_workspace_service import HISTORY_LIMIT, ApiWorkspaceService


def _record(service: ApiWorkspaceService, url: str) -> None:
    service.add_history(ApiRequest(url=url), status_code=200, elapsed_ms=1, size_bytes=2, body="{}")


def test_default_environments(tmp_path: Path) -> None:
    service = ApiWorkspaceService(tmp_path)

    assert set(service.get_environments()) == {"Dev", "Test", "QA", "Prod"}
    assert service.get_active_environment() == "Dev"


def test_set_environment_persists(tmp_path: Path) -> None:
    ApiWorkspaceService(tmp_path).set_environment("Dev", {"base_url": "https://dev.test"})

    environments = ApiWorkspaceService(tmp_path).get_environments()
    assert environments["Dev"] == {"base_url": "https://dev.test"}


def test_history_newest_first_and_limited(tmp_path: Path) -> None:
    service = ApiWorkspaceService(tmp_path)

    for i in range(HISTORY_LIMIT + 5):
        _record(service, f"https://x.test/{i}")

    history = service.get_history()
    assert len(history) == HISTORY_LIMIT
    assert history[0]["request"]["url"].endswith(str(HISTORY_LIMIT + 4))


def test_clear_history(tmp_path: Path) -> None:
    service = ApiWorkspaceService(tmp_path)
    _record(service, "https://x.test")
    service.clear_history()

    assert service.get_history() == []


def test_collections_save_overwrite_delete(tmp_path: Path) -> None:
    service = ApiWorkspaceService(tmp_path)
    service.save_to_collection("Users", "list", ApiRequest(url="https://x.test/1"))
    service.save_to_collection("Users", "list", ApiRequest(url="https://x.test/2"))

    items = service.get_collections()["Users"]
    assert len(items) == 1
    assert items[0]["request"]["url"] == "https://x.test/2"

    service.delete_from_collection("Users", "list")
    assert "Users" not in service.get_collections()


def test_corrupt_file_falls_back_to_defaults(tmp_path: Path) -> None:
    (tmp_path / "api_workspace.json").write_text("not json", encoding="utf-8")

    assert ApiWorkspaceService(tmp_path).get_history() == []
