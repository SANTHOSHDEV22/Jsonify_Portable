"""Tests for schema-driven fake payload generation."""

from __future__ import annotations

from jsonify.core.payload_generator import generate_payload, generate_payloads
from jsonify.core.schema_inference import infer_schema


def test_generates_object_matching_property_types() -> None:
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "active": {"type": "boolean"},
        },
        "required": ["id", "name", "active"],
    }

    payload = generate_payload(schema, seed=1)

    assert isinstance(payload, dict)
    assert isinstance(payload["id"], int)
    assert isinstance(payload["name"], str)
    assert isinstance(payload["active"], bool)


def test_optional_fields_excluded_when_include_optional_false() -> None:
    schema = {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "nickname": {"type": "string"}},
        "required": ["id"],
    }

    payload = generate_payload(schema, include_optional=False, seed=1)

    assert payload == {"id": payload["id"]}
    assert "nickname" not in payload


def test_enum_values_are_respected() -> None:
    schema = {"type": "string", "enum": ["red", "green", "blue"]}

    for seed in range(10):
        assert generate_payload(schema, seed=seed) in {"red", "green", "blue"}


def test_number_respects_minimum_and_maximum() -> None:
    schema = {"type": "integer", "minimum": 5, "maximum": 8}

    for seed in range(20):
        value = generate_payload(schema, seed=seed)
        assert 5 <= value <= 8


def test_array_item_count_within_bounds() -> None:
    schema = {"type": "array", "items": {"type": "integer"}}

    for seed in range(10):
        value = generate_payload(schema, array_min=2, array_max=4, seed=seed)
        assert 2 <= len(value) <= 4
        assert all(isinstance(item, int) for item in value)


def test_array_respects_min_items_and_max_items_from_schema() -> None:
    schema = {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 1}

    value = generate_payload(schema, seed=1)

    assert len(value) == 1


def test_email_hint_produces_email_like_string() -> None:
    schema = {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}

    payload = generate_payload(schema, seed=1)

    assert "@" in payload["email"]


def test_seed_makes_generation_deterministic() -> None:
    schema = {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
        "required": ["id", "name"],
    }

    first = generate_payload(schema, seed=42)
    second = generate_payload(schema, seed=42)

    assert first == second


def test_generate_payloads_returns_requested_count() -> None:
    schema = {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}

    payloads = generate_payloads(schema, 5, seed=1)

    assert len(payloads) == 5
    assert all(isinstance(p, dict) for p in payloads)


def test_generated_payload_matches_inferred_schema_shape() -> None:
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "tags"],
    }

    payload = generate_payload(schema, seed=3)
    regenerated = infer_schema(payload)

    assert regenerated["properties"]["id"]["type"] == "integer"
    assert regenerated["properties"]["tags"]["type"] == "array"


def test_nested_object_generation() -> None:
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "email": {"type": "string"}},
                "required": ["id", "email"],
            }
        },
        "required": ["user"],
    }

    payload = generate_payload(schema, seed=1)

    assert isinstance(payload["user"], dict)
    assert isinstance(payload["user"]["id"], int)
    assert "@" in payload["user"]["email"]


def test_null_type_generates_none() -> None:
    assert generate_payload({"type": "null"}, seed=1) is None
