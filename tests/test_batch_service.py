"""Tests for batch file processing."""

from __future__ import annotations

import json
from pathlib import Path

from jsonify.services.batch_service import BatchService


def _write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def test_expand_inputs_files_folders_and_globs(tmp_path: Path) -> None:
    a = _write(tmp_path, "a.json", "{}")
    sub = tmp_path / "sub"
    sub.mkdir()
    b = _write(sub, "b.jsonl", "{}")
    _write(tmp_path, "notes.txt", "x")

    assert set(BatchService.expand_inputs([tmp_path])) == {a, b}
    assert BatchService.expand_inputs([str(tmp_path / "*.json")]) == [a]
    assert BatchService.expand_inputs([a, a]) == [a]


def test_validate_reports_each_file(tmp_path: Path) -> None:
    good = _write(tmp_path, "good.json", '{"a": 1}')
    bad = _write(tmp_path, "bad.json", '{"a": ')

    results = BatchService().process_files([good, bad], "validate")

    assert [r.ok for r in results] == [True, False]
    assert "Invalid JSON" in results[1].message


def test_format_writes_new_file_and_keeps_source(tmp_path: Path) -> None:
    source = _write(tmp_path, "data.json", '{"b":1,"a":2}')

    result = BatchService().process_file(source, "format", indent=4)

    assert result.ok
    assert result.output_path == tmp_path / "data.formatted.json"
    assert '    "b": 1' in result.output_path.read_text(encoding="utf-8")
    assert source.read_text(encoding="utf-8") == '{"b":1,"a":2}'


def test_minify_and_output_dir(tmp_path: Path) -> None:
    source = _write(tmp_path, "data.json", '{\n  "a": 1\n}')
    out = tmp_path / "out"

    result = BatchService().process_file(source, "minify", output_dir=out)

    assert result.output_path == out / "data.min.json"
    assert result.output_path.read_text(encoding="utf-8") == '{"a":1}'


def test_in_place_overwrites_json_outputs(tmp_path: Path) -> None:
    source = _write(tmp_path, "data.json", '{"a":1}')

    BatchService().process_file(source, "format", in_place=True)

    assert json.loads(source.read_text(encoding="utf-8")) == {"a": 1}
    assert "\n" in source.read_text(encoding="utf-8")


def test_mask_operation_masks_sensitive_values(tmp_path: Path) -> None:
    source = _write(tmp_path, "data.json", '{"email": "alice@example.com", "n": 1}')

    result = BatchService().process_file(source, "mask")

    masked = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert masked["email"] != "alice@example.com"
    assert masked["n"] == 1


def test_convert_operations(tmp_path: Path) -> None:
    source = _write(tmp_path, "rows.json", '[{"id": 1, "name": "A"}]')

    yaml_result = BatchService().process_file(source, "yaml")
    csv_result = BatchService().process_file(source, "csv")

    assert "name: A" in yaml_result.output_path.read_text(encoding="utf-8")
    assert "id,name" in csv_result.output_path.read_text(encoding="utf-8")


def test_csv_of_non_array_fails_gracefully(tmp_path: Path) -> None:
    source = _write(tmp_path, "obj.json", '{"a": 1}')

    result = BatchService().process_file(source, "csv")

    assert not result.ok
    assert "array of objects" in result.message


def test_jsonl_files_are_parsed(tmp_path: Path) -> None:
    source = _write(tmp_path, "rows.jsonl", '{"id": 1}\n{"id": 2}\n')

    result = BatchService().process_file(source, "validate")

    assert result.ok


def test_unknown_operation_and_missing_file(tmp_path: Path) -> None:
    source = _write(tmp_path, "a.json", "{}")

    assert not BatchService().process_file(source, "explode").ok
    assert not BatchService().process_file(tmp_path / "nope.json", "validate").ok


def test_utf8_bom_is_tolerated(tmp_path: Path) -> None:
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}')

    assert BatchService().process_file(path, "validate").ok
