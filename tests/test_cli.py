"""Tests for the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jsonify.cli import main


def _write(folder: Path, name: str, text: str) -> str:
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _write(tmp_path, "a.json", '{"b":1,"a":2}')

    assert main(["format", source, "--sort-keys", "-i", "4"]) == 0

    out = capsys.readouterr().out
    assert out.index('"a"') < out.index('"b"')
    assert '    "a": 2' in out


def test_format_in_place(tmp_path: Path) -> None:
    source = _write(tmp_path, "a.json", '{"a":1}')

    assert main(["format", source, "--in-place"]) == 0
    assert "\n" in Path(source).read_text(encoding="utf-8")


def test_minify(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _write(tmp_path, "a.json", '{\n "a": [1, 2]\n}')

    main(["minify", source])

    assert capsys.readouterr().out.strip() == '{"a":[1,2]}'


def test_validate_exit_codes(tmp_path: Path) -> None:
    good = _write(tmp_path, "good.json", "{}")
    bad = _write(tmp_path, "bad.json", "{")

    assert main(["validate", good]) == 0
    assert main(["validate", good, bad]) == 1


def test_invalid_input_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = _write(tmp_path, "bad.json", "{")

    assert main(["format", bad]) == 2
    assert "invalid JSON" in capsys.readouterr().err


def test_missing_file_is_a_usage_error(tmp_path: Path) -> None:
    assert main(["format", str(tmp_path / "missing.json")]) == 2


def test_diff(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    old = _write(tmp_path, "old.json", '{"a": 1, "b": 2}')
    new = _write(tmp_path, "new.json", '{"a": 1}')
    same = _write(tmp_path, "same.json", '{"a": 1, "b": 2}')

    assert main(["diff", old, same]) == 0
    assert main(["diff", old, new]) == 1
    assert "$.b" in capsys.readouterr().out


def test_diff_with_identity_key_and_report(tmp_path: Path) -> None:
    old = _write(tmp_path, "old.json", '[{"id": 1, "v": 1}, {"id": 2, "v": 2}]')
    new = _write(tmp_path, "new.json", '[{"id": 2, "v": 2}, {"id": 1, "v": 1}]')
    report = tmp_path / "report.md"

    assert main(["diff", old, new, "--key", "id", "--report", str(report)]) == 0
    assert "No differences" in report.read_text(encoding="utf-8")


def test_mask(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _write(tmp_path, "a.json", '{"email": "alice@example.com"}')

    assert main(["mask", source]) == 0
    assert "alice@example.com" not in capsys.readouterr().out


def test_convert_both_directions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _write(tmp_path, "a.json", '{"name": "A"}')

    main(["convert", source, "--to", "yaml"])
    assert "name: A" in capsys.readouterr().out

    yaml_file = _write(tmp_path, "a.yaml", "name: A\ncount: 2\n")
    main(["convert", yaml_file, "--from", "yaml"])
    assert json.loads(capsys.readouterr().out) == {"name": "A", "count": 2}


def test_query_jq_and_jsonpath(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _write(tmp_path, "a.json", '{"users": [{"name": "A"}, {"name": "B"}]}')

    main(["query", source, ".users[] | .name"])
    assert capsys.readouterr().out.split() == ['"A"', '"B"']

    main(["query", source, "$.users[*].name", "--jsonpath"])
    assert capsys.readouterr().out.split() == ['"A"', '"B"']

    assert main(["query", source, "not_a_filter"]) == 2


def test_schema_generate_and_validate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _write(tmp_path, "a.json", '{"id": 1}')

    main(["schema", source])
    schema_text = capsys.readouterr().out
    schema = _write(tmp_path, "schema.json", schema_text)

    assert main(["schema", source, "--validate", schema]) == 0
    bad = _write(tmp_path, "bad.json", '{"id": "x"}')
    assert main(["schema", bad, "--validate", schema]) == 1


def test_codegen(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _write(tmp_path, "a.json", '{"id": 1}')

    main(["codegen", source, "--lang", "typescript", "--name", "Thing"])

    assert "export interface Thing" in capsys.readouterr().out


def test_batch(tmp_path: Path) -> None:
    _write(tmp_path, "a.json", '{"a":1}')
    _write(tmp_path, "b.json", '{"b":2}')
    out = tmp_path / "out"

    assert main(["batch", "format", str(tmp_path), "-o", str(out)]) == 0
    assert {p.name for p in out.iterdir()} == {"a.formatted.json", "b.formatted.json"}


def test_batch_with_no_matches(tmp_path: Path) -> None:
    assert main(["batch", "format", str(tmp_path / "*.nothing")]) == 2


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: jsonify" in capsys.readouterr().out
