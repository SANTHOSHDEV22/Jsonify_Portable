"""Tests for the GraphService application service."""

from __future__ import annotations

from pathlib import Path

import pytest

from jsonify.services.graph_service import GraphService


@pytest.fixture
def graph_service(
    tmp_path: Path,
) -> GraphService:
    """Create GraphService using pytest's temporary directory."""

    return GraphService(
        temp_directory=tmp_path
    )


def test_get_temp_path(
    graph_service: GraphService,
    tmp_path: Path,
) -> None:
    """GraphService should return the expected temporary path."""

    result = graph_service.get_temp_path()

    assert result == (
        tmp_path
        / "jsonify_graph_view.html"
    )


def test_save_html(
    graph_service: GraphService,
) -> None:
    """GraphService should save HTML to disk."""

    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Jsonify</h1>
    </body>
    </html>
    """

    result = graph_service.save_html(html)

    assert result.exists()

    assert result.read_text(
        encoding="utf-8"
    ) == html


def test_exists_before_save(
    graph_service: GraphService,
) -> None:
    """Graph file should not initially exist."""

    assert graph_service.exists() is False


def test_exists_after_save(
    graph_service: GraphService,
) -> None:
    """Graph file should exist after saving."""

    graph_service.save_html(
        "<html></html>"
    )

    assert graph_service.exists() is True


def test_delete(
    graph_service: GraphService,
) -> None:
    """GraphService should delete an existing graph file."""

    graph_service.save_html(
        "<html></html>"
    )

    assert graph_service.exists() is True

    graph_service.delete()

    assert graph_service.exists() is False


def test_delete_when_file_does_not_exist(
    graph_service: GraphService,
) -> None:
    """Deleting a missing graph should not raise an error."""

    assert graph_service.exists() is False

    graph_service.delete()

    assert graph_service.exists() is False


def test_save_html_overwrites_existing_file(
    graph_service: GraphService,
) -> None:
    """Saving again should replace the previous graph HTML."""

    graph_service.save_html(
        "<html>first</html>"
    )

    graph_service.save_html(
        "<html>second</html>"
    )

    result = graph_service.get_temp_path()

    assert result.read_text(
        encoding="utf-8"
    ) == "<html>second</html>"


def test_save_html_rejects_non_string(
    graph_service: GraphService,
) -> None:
    """GraphService should reject non-string HTML."""

    with pytest.raises(TypeError):
        graph_service.save_html(123)  # type: ignore[arg-type]