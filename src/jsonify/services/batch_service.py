"""Batch processing of many JSON files (used by both the GUI and the CLI)."""

from __future__ import annotations

import glob
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from jsonify.core.converters import (
    ConversionError,
    json_to_csv,
    json_to_xml,
    json_to_yaml,
)
from jsonify.core.formatter import beautify, minify, normalize
from jsonify.core.models import JSONValue
from jsonify.core.parser import parse_multiple_json
from jsonify.core.sensitive import safe_mask

JSON_SUFFIXES = (".json", ".jsonl", ".ndjson")

# operation -> (output suffix, description); ``None`` suffix = no output file.
OPERATIONS: dict[str, tuple[str | None, str]] = {
    "validate": (None, "Check that each file is valid JSON"),
    "format": (".formatted.json", "Pretty-print"),
    "minify": (".min.json", "Remove all whitespace"),
    "normalize": (".normalized.json", "Sort keys recursively and pretty-print"),
    "mask": (".masked.json", "Auto-mask detected sensitive values"),
    "yaml": (".yaml", "Convert to YAML"),
    "xml": (".xml", "Convert to XML"),
    "csv": (".csv", "Convert an array of objects to CSV"),
}


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Outcome of processing one file."""

    path: Path
    ok: bool
    message: str
    output_path: Path | None = None


class BatchService:
    """Validate/format/mask/convert many files with one call."""

    @staticmethod
    def expand_inputs(inputs: Iterable[str | Path]) -> list[Path]:
        """Expand files, folders (recursively) and glob patterns into file paths."""

        found: dict[Path, None] = {}

        for raw in inputs:
            text = str(raw)
            path = Path(text)

            if path.is_dir():
                for suffix in JSON_SUFFIXES:
                    for found_path in sorted(path.rglob(f"*{suffix}")):
                        found.setdefault(found_path, None)
            elif path.is_file():
                found.setdefault(path, None)
            else:
                for pattern_match in sorted(glob.glob(text, recursive=True)):
                    candidate = Path(pattern_match)
                    if candidate.is_file():
                        found.setdefault(candidate, None)

        return list(found)

    def process_files(
        self,
        paths: Iterable[Path],
        operation: str,
        *,
        output_dir: Path | None = None,
        indent: int = 2,
        in_place: bool = False,
    ) -> list[BatchResult]:
        """Process every path; one failure never stops the rest."""

        return [
            self.process_file(
                path, operation, output_dir=output_dir, indent=indent, in_place=in_place
            )
            for path in paths
        ]

    def process_file(
        self,
        path: Path,
        operation: str,
        *,
        output_dir: Path | None = None,
        indent: int = 2,
        in_place: bool = False,
    ) -> BatchResult:
        if operation not in OPERATIONS:
            return BatchResult(path, False, f"Unknown operation: {operation}")

        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as error:
            return BatchResult(path, False, f"Could not read file: {error}")

        try:
            payload = self._parse(path, text)
        except json.JSONDecodeError as error:
            return BatchResult(
                path,
                False,
                f"Invalid JSON: {error.msg} (line {error.lineno}, column {error.colno})",
            )

        suffix = OPERATIONS[operation][0]
        if suffix is None:
            return BatchResult(path, True, "Valid JSON")

        try:
            content = self._render(operation, payload, indent)
        except ConversionError as error:
            return BatchResult(path, False, str(error))

        destination = self._destination(
            path, suffix, output_dir, in_place and suffix.endswith(".json")
        )

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        except OSError as error:
            return BatchResult(path, False, f"Could not write output: {error}")

        return BatchResult(path, True, "OK", destination)

    # -----------------------------------------------------------------

    @staticmethod
    def _parse(path: Path, text: str) -> JSONValue:
        if path.suffix.lower() in (".jsonl", ".ndjson"):
            return parse_multiple_json(text)[0]
        return json.loads(text)

    @staticmethod
    def _render(operation: str, payload: JSONValue, indent: int) -> str:
        if operation == "format":
            return beautify(payload, indent=indent)
        if operation == "minify":
            return minify(payload)
        if operation == "normalize":
            return beautify(normalize(payload), indent=indent)
        if operation == "mask":
            return beautify(safe_mask(payload)[0], indent=indent)
        if operation == "yaml":
            return json_to_yaml(payload)
        if operation == "xml":
            return json_to_xml(payload)
        if operation == "csv":
            return json_to_csv(payload)
        raise ConversionError(f"Unknown operation: {operation}")

    @staticmethod
    def _destination(path: Path, suffix: str, output_dir: Path | None, overwrite: bool) -> Path:
        if overwrite:
            return path

        folder = output_dir if output_dir is not None else path.parent
        return folder / f"{path.stem}{suffix}"
