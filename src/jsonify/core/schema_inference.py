"""Infer a JSON Schema (Draft 2020-12) from a sample JSON payload."""

from __future__ import annotations

from typing import Any

from jsonify.core.models import JSONValue


def infer_schema_from_samples(samples: list[JSONValue]) -> dict[str, Any]:
    """Infer one schema from several *separate* sample documents (e.g. several
    API responses), rather than one array.

    A field present, non-null, on every sample comes out required; a field
    only some samples have comes out optional — the same "required = present
    everywhere" rule ``infer_schema`` already applies to items of one array,
    just applied across independent documents instead.
    """

    return merge_schemas([infer_schema(sample) for sample in samples])


def infer_schema(value: JSONValue) -> dict[str, Any]:
    """Infer a JSON Schema fragment describing ``value``'s shape."""

    if value is None:
        return {"type": "null"}

    if isinstance(value, bool):
        return {"type": "boolean"}

    if isinstance(value, int):
        return {"type": "integer"}

    if isinstance(value, float):
        return {"type": "number"}

    if isinstance(value, str):
        return {"type": "string"}

    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}

        return {
            "type": "array",
            "items": merge_schemas([infer_schema(item) for item in value]),
        }

    if isinstance(value, dict):
        properties = {key: infer_schema(item) for key, item in value.items()}
        return {
            "type": "object",
            "properties": properties,
            "required": sorted(value.keys()),
        }

    return {}


def merge_schemas(schemas: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge several inferred schemas for values seen at the same position
    (e.g. items of one array) into a single representative schema."""

    if not schemas:
        return {}

    types = {schema.get("type") for schema in schemas}

    if len(types) == 1:
        (only_type,) = types
        if only_type == "object":
            return _merge_object_schemas(schemas)
        return schemas[0]

    return {"type": sorted(t for t in types if t)}


def _merge_object_schemas(schemas: list[dict[str, Any]]) -> dict[str, Any]:
    merged_properties: dict[str, Any] = {}
    key_sets: list[set[str]] = []

    for schema in schemas:
        properties = schema.get("properties", {})
        key_sets.append(set(properties))

        for key, value_schema in properties.items():
            if key in merged_properties:
                merged_properties[key] = merge_schemas([merged_properties[key], value_schema])
            else:
                merged_properties[key] = value_schema

    common_keys = set.intersection(*key_sets) if key_sets else set()

    return {
        "type": "object",
        "properties": merged_properties,
        "required": sorted(common_keys),
    }
