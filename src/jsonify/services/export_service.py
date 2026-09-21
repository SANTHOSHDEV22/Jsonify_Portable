"""Export service for Jsonify."""

from __future__ import annotations

import json
from pathlib import Path

from jsonify.core.models import JSONValue


class ExportError(RuntimeError):
    """Raised when Jsonify cannot export data."""


class ExportService:
    """Provides JSON and text export operations."""

    def export_json(
        self,
        payload: JSONValue,
        file_path: str | Path,
        *,
        indent: int = 2,
    ) -> Path:
        """Export a JSON payload to a formatted JSON file."""

        path = self._ensure_extension(
            file_path,
            ".json",
        )

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_text(
                json.dumps(
                    payload,
                    indent=indent,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        except (OSError, TypeError, ValueError) as error:
            raise ExportError(f"Unable to export JSON: {error}") from error

        return path

    def export_text(
        self,
        content: str,
        file_path: str | Path,
        *,
        extension: str,
    ) -> Path:
        """Export arbitrary text content."""

        if not extension.startswith("."):
            extension = f".{extension}"

        path = self._ensure_extension(
            file_path,
            extension,
        )

        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            path.write_text(
                content,
                encoding="utf-8",
            )

        except OSError as error:
            raise ExportError(f"Unable to export file: {error}") from error

        return path

    @staticmethod
    def _ensure_extension(
        file_path: str | Path,
        extension: str,
    ) -> Path:
        """Ensure a path has the requested extension."""

        path = Path(file_path)

        if path.suffix.lower() != extension.lower():
            path = path.with_suffix(extension)

        return path
