"""Tests for JSON <-> YAML/XML/CSV conversion."""

from __future__ import annotations

import pytest

from jsonify.core.converters import (
    ConversionError,
    csv_to_json,
    json_to_csv,
    json_to_xml,
    json_to_yaml,
    xml_to_json,
    yaml_to_json,
)


def test_json_to_yaml_and_back() -> None:
    payload = {"name": "Alice", "age": 30, "tags": ["a", "b"]}

    yaml_text = json_to_yaml(payload)
    assert yaml_to_json(yaml_text) == payload


def test_yaml_to_json_invalid() -> None:
    with pytest.raises(ConversionError):
        yaml_to_json("key: [unbalanced")


def test_json_to_xml_and_back_object() -> None:
    payload = {"name": "Alice", "age": 30}

    xml_text = json_to_xml(payload)
    assert xml_to_json(xml_text) == {"name": "Alice", "age": 30}


def test_json_to_xml_and_back_array() -> None:
    payload = {"users": [{"name": "Alice"}, {"name": "Bob"}]}

    xml_text = json_to_xml(payload)
    assert xml_to_json(xml_text) == payload


def test_json_to_xml_scalar_types_round_trip() -> None:
    payload = {"active": True, "inactive": False, "count": 3, "ratio": 1.5, "empty": None}

    result = xml_to_json(json_to_xml(payload))

    assert result["active"] is True
    assert result["inactive"] is False
    assert result["count"] == 3
    assert result["ratio"] == 1.5
    assert result["empty"] is None


def test_xml_to_json_invalid() -> None:
    with pytest.raises(ConversionError):
        xml_to_json("<not><closed>")


def test_json_to_csv_basic() -> None:
    payload = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    csv_text = json_to_csv(payload)

    assert "id,name" in csv_text
    assert "1,Alice" in csv_text
    assert "2,Bob" in csv_text


def test_json_to_csv_requires_array_of_objects() -> None:
    with pytest.raises(ConversionError):
        json_to_csv({"a": 1})


def test_csv_to_json_round_trip() -> None:
    payload = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]

    csv_text = json_to_csv(payload)
    result = csv_to_json(csv_text)

    assert result == payload
