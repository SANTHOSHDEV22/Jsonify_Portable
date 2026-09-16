"""Graph output service for Jsonify."""

from __future__ import annotations

import tempfile
from pathlib import Path


class GraphService:
    """
    Handles temporary HTML files generated for graph visualization.

    This keeps file-system operations outside the UI layer.
    """

    _TEMP_FILENAME = "jsonify_graph_view.html"

    def __init__(
        self,
        temp_directory: Path | None = None,
    ) -> None:
        """
        Initialize the graph service.

        Args:
            temp_directory:
                Optional directory for temporary graph files.
                The operating system temporary directory is used
                when no directory is provided.
        """
        self._temp_directory = (
            temp_directory if temp_directory is not None else Path(tempfile.gettempdir())
        )

    def get_temp_path(self) -> Path:
        """
        Return the temporary graph HTML file path.

        Returns:
            Path to the graph HTML file.
        """
        return self._temp_directory / self._TEMP_FILENAME

    def save_html(
        self,
        html: str,
    ) -> Path:
        """
        Save graph HTML to the temporary graph file.

        Args:
            html: Complete HTML content.

        Returns:
            Path of the generated HTML file.
        """
        if not isinstance(html, str):
            raise TypeError("Graph HTML must be a string.")

        path = self.get_temp_path()

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            html,
            encoding="utf-8",
        )

        return path

    def exists(self) -> bool:
        """
        Check whether the temporary graph file exists.

        Returns:
            True if the graph file exists.
        """
        return self.get_temp_path().is_file()

    def delete(self) -> None:
        """Delete the temporary graph file if it exists."""
        path = self.get_temp_path()

        if path.exists():
            path.unlink()
