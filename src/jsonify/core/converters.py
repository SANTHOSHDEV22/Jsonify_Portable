"""Conversions between JSON and YAML / XML / CSV."""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ElementTree

import yaml

from jsonify.core.models import JSONValue
from jsonify.core.traversal import to_table_rows


class ConversionError(ValueError):
    """Raised when a conversion to/from JSON fails."""


# ---------------------------------------------------------------------
# YAML
# ---------------------------------------------------------------------


def json_to_yaml(data: JSONValue) -> str:
    """Render a JSON value as YAML."""

    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def yaml_to_json(text: str) -> JSONValue:
    """Parse YAML text into a JSON-compatible value."""

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ConversionError(f"Invalid YAML: {error}") from error


# ---------------------------------------------------------------------
# XML
#
# There's no single canonical JSON<->XML mapping, so this uses a simple,
# documented convention: object keys become element names, list items
# become repeated <item> elements, and scalars become element text.
# Round-tripping json_to_xml -> xml_to_json is lossless for JSON built
# from that same convention; arbitrary hand-written XML may not convert
# back to an equivalent JSON shape.
# ---------------------------------------------------------------------

_UNSAFE_TAG_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


def json_to_xml(data: JSONValue, *, root_tag: str = "root") -> str:
    """Render a JSON value as XML."""

    root = ElementTree.Element(_safe_tag(root_tag))
    _build_xml(root, data)
    return ElementTree.tostring(root, encoding="unicode")


def xml_to_json(text: str) -> JSONValue:
    """Parse XML text back into a JSON value (see module docstring)."""

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise ConversionError(f"Invalid XML: {error}") from error

    return _element_to_json(root)


def _safe_tag(key: str) -> str:
    tag = _UNSAFE_TAG_CHARS.sub("_", str(key)) or "_"
    return f"_{tag}" if tag[0].isdigit() else tag


def _build_xml(parent: ElementTree.Element, value: JSONValue) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            child = ElementTree.SubElement(parent, _safe_tag(key))
            _build_xml(child, item)
    elif isinstance(value, list):
        for item in value:
            child = ElementTree.SubElement(parent, "item")
            _build_xml(child, item)
    else:
        parent.text = _scalar_to_text(value)


def _scalar_to_text(value: JSONValue) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _element_to_json(element: ElementTree.Element) -> JSONValue:
    children = list(element)

    if not children:
        return _text_to_scalar(element.text)

    tags = {child.tag for child in children}
    if tags == {"item"}:
        return [_element_to_json(child) for child in children]

    return {child.tag: _element_to_json(child) for child in children}


def _text_to_scalar(text: str | None) -> JSONValue:
    if text is None:
        return None

    stripped = text.strip()
    if not stripped:
        return None
    if stripped == "true":
        return True
    if stripped == "false":
        return False

    try:
        if "." in stripped or "e" in stripped.lower():
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


# ---------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------


def json_to_csv(data: JSONValue) -> str:
    """Render an array of objects as CSV. Non-scalar cells are JSON-encoded."""

    columns, rows = to_table_rows(data)

    if not columns:
        raise ConversionError("CSV export requires a JSON array of objects.")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)

    for row in rows:
        writer.writerow([_csv_cell(cell) for cell in row])

    return buffer.getvalue()


def csv_to_json(text: str) -> list[dict[str, JSONValue]]:
    """Parse CSV text into a list of objects (all values as strings)."""

    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _csv_cell(value: JSONValue) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
