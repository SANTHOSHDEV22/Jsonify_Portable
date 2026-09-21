"""Tests for JSON Schema inference from sample payloads."""

from __future__ import annotations

from jsonify.core.schema_inference import infer_schema, merge_schemas


def test_infer_scalar_types() -> None:
    assert infer_schema(None) == {"type": "null"}
    assert infer_schema(True) == {"type": "boolean"}
    assert infer_schema(1) == {"type": "integer"}
    assert infer_schema(1.5) == {"type": "number"}
    assert infer_schema("x") == {"type": "string"}


def test_infer_object() -> None:
    schema = infer_schema({"name": "Alice", "age": 30})

    assert schema["type"] == "object"
    assert schema["properties"]["name"] == {"type": "string"}
    assert schema["properties"]["age"] == {"type": "integer"}
    assert schema["required"] == ["age", "name"]


def test_infer_nested_object() -> None:
    schema = infer_schema({"user": {"name": "Alice"}})

    assert schema["properties"]["user"]["type"] == "object"
    assert schema["properties"]["user"]["properties"]["name"] == {"type": "string"}


def test_infer_array_of_scalars() -> None:
    schema = infer_schema([1, 2, 3])

    assert schema == {"type": "array", "items": {"type": "integer"}}


def test_infer_empty_array() -> None:
    assert infer_schema([]) == {"type": "array", "items": {}}


def test_infer_array_of_objects_merges_shape() -> None:
    schema = infer_schema([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])

    items_schema = schema["items"]
    assert items_schema["type"] == "object"
    assert set(items_schema["properties"]) == {"id", "name"}
    assert items_schema["required"] == ["id", "name"]


def test_infer_array_of_objects_with_inconsistent_keys() -> None:
    schema = infer_schema([{"id": 1, "name": "A"}, {"id": 2}])

    items_schema = schema["items"]
    assert set(items_schema["properties"]) == {"id", "name"}
    # Only keys common to every item are required.
    assert items_schema["required"] == ["id"]


def test_merge_schemas_mixed_types() -> None:
    merged = merge_schemas([{"type": "integer"}, {"type": "string"}])

    assert merged == {"type": ["integer", "string"]}


def test_merge_schemas_empty() -> None:
    assert merge_schemas([]) == {}
