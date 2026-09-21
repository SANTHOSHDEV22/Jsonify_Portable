"""Command-line interface for Jsonify.

Everything here uses the same core/service layer as the desktop app and
never imports Qt, so it works on servers and in CI without a display.

Exit codes: 0 success, 1 the check found problems (invalid JSON, differences),
2 usage or I/O error.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jsonify import __version__
from jsonify.core.breaking_changes import classify_diff
from jsonify.core.codegen import SUPPORTED_LANGUAGES, generate_code
from jsonify.core.converters import (
    ConversionError,
    csv_to_json,
    json_to_csv,
    json_to_xml,
    json_to_yaml,
    xml_to_json,
    yaml_to_json,
)
from jsonify.core.diff import compare_json
from jsonify.core.diff_report import render_diff_report
from jsonify.core.formatter import beautify, minify
from jsonify.core.jq import JqQueryError, run_jq
from jsonify.core.models import JSONValue
from jsonify.core.sensitive import safe_mask
from jsonify.services.batch_service import OPERATIONS, BatchService
from jsonify.services.jsonpath_service import JsonPathQueryError, JsonPathService
from jsonify.services.schema_service import JsonSchemaError, SchemaService

VERSION = __version__

COMMANDS = (
    "format",
    "minify",
    "validate",
    "diff",
    "mask",
    "convert",
    "query",
    "schema",
    "codegen",
    "batch",
)


class CliError(Exception):
    """A user-facing error (printed to stderr, exit code 2)."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jsonify",
        description="Jsonify — inspect, transform and validate JSON. "
        "Run with no command to open the desktop app.",
    )
    parser.add_argument("--version", action="version", version=f"jsonify {VERSION}")
    sub = parser.add_subparsers(dest="command", metavar="command")

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=help_text, description=help_text)

    p = add("format", "Pretty-print JSON")
    p.add_argument("file", help="JSON file, or - for stdin")
    p.add_argument("-i", "--indent", type=int, default=2)
    p.add_argument("--sort-keys", action="store_true")
    p.add_argument("-o", "--output", help="write here instead of stdout")
    p.add_argument("--in-place", action="store_true", help="overwrite the input file")

    p = add("minify", "Remove all whitespace from JSON")
    p.add_argument("file")
    p.add_argument("-o", "--output")

    p = add("validate", "Check that files are valid JSON")
    p.add_argument("files", nargs="+", help="files, folders or glob patterns")

    p = add("diff", "Compare two JSON files")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--key", help="match array items by this key instead of position")
    p.add_argument("--breaking", action="store_true", help="show only breaking changes")
    p.add_argument("--report", help="also write a Markdown report to this path")

    p = add("mask", "Mask detected sensitive values (emails, tokens, keys, ...)")
    p.add_argument("file")
    p.add_argument("-o", "--output")

    p = add("convert", "Convert between JSON and YAML/XML/CSV")
    p.add_argument("file")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--to", choices=("yaml", "xml", "csv"), help="convert JSON to this format")
    group.add_argument(
        "--from", dest="source", choices=("yaml", "xml", "csv"), help="convert this format to JSON"
    )
    p.add_argument("-o", "--output")

    p = add("query", "Run a jq-lite or JSONPath query")
    p.add_argument("file")
    p.add_argument("expression")
    p.add_argument("--jsonpath", action="store_true", help="treat the expression as JSONPath")

    p = add("schema", "Generate a JSON Schema, or validate against one")
    p.add_argument("file")
    p.add_argument("--validate", metavar="SCHEMA", help="validate the file against this schema")
    p.add_argument("-o", "--output")

    p = add("codegen", "Generate model code from a JSON sample")
    p.add_argument("file")
    p.add_argument("--lang", required=True, choices=SUPPORTED_LANGUAGES)
    p.add_argument("--name", default="Root", help="name of the root type")

    p = add("batch", "Process many files at once")
    p.add_argument("operation", choices=sorted(OPERATIONS))
    p.add_argument("inputs", nargs="+", help="files, folders or glob patterns")
    p.add_argument("-o", "--output-dir")
    p.add_argument("-i", "--indent", type=int, default=2)
    p.add_argument("--in-place", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        return _COMMAND_HANDLERS[args.command](args)
    except CliError as error:
        print(f"jsonify: error: {error}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _read_text(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    try:
        return Path(source).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise CliError(f"cannot read {source}: {error}") from error


def _load_json(source: str) -> JSONValue:
    text = _read_text(source)
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise CliError(
            f"{source}: invalid JSON: {error.msg} (line {error.lineno}, column {error.colno})"
        ) from error


def _emit(text: str, output: str | None) -> None:
    if output:
        try:
            Path(output).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        except OSError as error:
            raise CliError(f"cannot write {output}: {error}") from error
    else:
        print(text)


# ---------------------------------------------------------------------
# command handlers
# ---------------------------------------------------------------------


def _cmd_format(args: argparse.Namespace) -> int:
    payload = _load_json(args.file)
    output = beautify(payload, indent=args.indent, sort_keys=args.sort_keys)

    if args.in_place:
        if args.file == "-":
            raise CliError("--in-place needs a file, not stdin")
        _emit(output, args.file)
    else:
        _emit(output, args.output)
    return 0


def _cmd_minify(args: argparse.Namespace) -> int:
    _emit(minify(_load_json(args.file)), args.output)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    paths = BatchService.expand_inputs(args.files)
    if not paths:
        raise CliError("no matching files found")

    results = BatchService().process_files(paths, "validate")
    for result in results:
        print(
            f"{'OK  ' if result.ok else 'FAIL'} {result.path}"
            + ("" if result.ok else f": {result.message}")
        )

    failed = sum(1 for r in results if not r.ok)
    print(f"\n{len(results) - failed}/{len(results)} valid", file=sys.stderr)
    return 1 if failed else 0


def _cmd_diff(args: argparse.Namespace) -> int:
    differences = compare_json(
        _load_json(args.old), _load_json(args.new), array_identity_key=args.key
    )

    if args.breaking:
        breaking_paths = {change.path for change in classify_diff(differences)}
        differences = [d for d in differences if d.path in breaking_paths]

    if args.report:
        _emit(render_diff_report(differences), args.report)

    if not differences:
        print("No differences.")
        return 0

    for diff in differences:
        print(f"{diff.symbol} {diff.path}")
    return 1


def _cmd_mask(args: argparse.Namespace) -> int:
    masked, findings = safe_mask(_load_json(args.file))
    _emit(beautify(masked), args.output)
    print(f"{len(findings)} value(s) masked", file=sys.stderr)
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    try:
        if args.to:
            payload = _load_json(args.file)
            converters = {"yaml": json_to_yaml, "xml": json_to_xml, "csv": json_to_csv}
            _emit(converters[args.to](payload), args.output)
        else:
            text = _read_text(args.file)
            readers: dict[str, Callable[[str], Any]] = {
                "yaml": yaml_to_json,
                "xml": xml_to_json,
                "csv": csv_to_json,
            }
            _emit(beautify(readers[args.source](text)), args.output)
    except ConversionError as error:
        raise CliError(str(error)) from error
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    payload = _load_json(args.file)

    try:
        if args.jsonpath:
            results: list[JSONValue] = [
                r.value for r in JsonPathService().query(payload, args.expression)
            ]
        else:
            results = run_jq(payload, args.expression)
    except (JqQueryError, JsonPathQueryError) as error:
        raise CliError(str(error)) from error

    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    return 0


def _cmd_schema(args: argparse.Namespace) -> int:
    payload = _load_json(args.file)
    service = SchemaService()

    if args.validate:
        schema = _load_json(args.validate)
        if not isinstance(schema, dict):
            raise CliError("the schema must be a JSON object")
        try:
            result = service.validate(payload, schema)
        except JsonSchemaError as error:
            raise CliError(str(error)) from error

        if result.valid:
            print("Valid.")
            return 0
        for problem in result.errors:
            print(f"{problem.path}: {problem.message}")
        return 1

    _emit(beautify(service.generate_schema(payload)), args.output)
    return 0


def _cmd_codegen(args: argparse.Namespace) -> int:
    print(generate_code(_load_json(args.file), args.lang, root_name=args.name))
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    paths = BatchService.expand_inputs(args.inputs)
    if not paths:
        raise CliError("no matching files found")

    output_dir = Path(args.output_dir) if args.output_dir else None
    results = BatchService().process_files(
        paths, args.operation, output_dir=output_dir, indent=args.indent, in_place=args.in_place
    )

    for result in results:
        target = f" -> {result.output_path}" if result.output_path else ""
        print(
            f"{'OK  ' if result.ok else 'FAIL'} {result.path}{target}"
            + ("" if result.ok else f": {result.message}")
        )

    failed = sum(1 for r in results if not r.ok)
    print(f"\n{len(results) - failed}/{len(results)} succeeded", file=sys.stderr)
    return 1 if failed else 0


_COMMAND_HANDLERS = {
    "format": _cmd_format,
    "minify": _cmd_minify,
    "validate": _cmd_validate,
    "diff": _cmd_diff,
    "mask": _cmd_mask,
    "convert": _cmd_convert,
    "query": _cmd_query,
    "schema": _cmd_schema,
    "codegen": _cmd_codegen,
    "batch": _cmd_batch,
}
