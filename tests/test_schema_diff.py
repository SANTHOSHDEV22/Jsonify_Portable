"""Tests for schema evolution / schema diffing."""

from __future__ import annotations

from jsonify.core.schema_diff import diff_payloads, diff_sample_sets, diff_schemas
from jsonify.core.schema_inference import infer_schema_from_samples


def _categories(changes) -> list[str]:
    return [c.category for c in changes]


def test_field_renamed_looks_like_remove_plus_add() -> None:
    old = {"id": 101, "name": "John", "email": "john@example.com"}
    new = {"id": 101, "fullName": "John", "email": "john@example.com"}

    changes = diff_payloads(old, new)

    assert set(_categories(changes)) == {"removed_field", "added_field"}
    paths = {c.path for c in changes}
    assert "$.name" in paths
    assert "$.fullName" in paths


def test_type_change_detected() -> None:
    changes = diff_payloads({"age": 30}, {"age": "thirty"})

    assert len(changes) == 1
    assert changes[0].category == "type_changed"
    assert changes[0].path == "$.age"
    assert "integer" in changes[0].detail and "string" in changes[0].detail


def test_no_changes_for_identical_shape() -> None:
    assert diff_payloads({"a": 1, "b": "x"}, {"a": 2, "b": "y"}) == []


def test_required_to_optional_and_back() -> None:
    old_samples = [{"id": 1, "email": "a@x.com"}, {"id": 2, "email": "b@x.com"}]
    new_samples = [{"id": 1, "email": "a@x.com"}, {"id": 2}]

    changes = diff_sample_sets(old_samples, new_samples)

    assert any(c.category == "became_optional" and c.path == "$.email" for c in changes)


def test_optional_becomes_required() -> None:
    old_samples = [{"id": 1}, {"id": 2, "note": "x"}]
    new_samples = [{"id": 1, "note": "y"}, {"id": 2, "note": "z"}]

    changes = diff_sample_sets(old_samples, new_samples)

    assert any(c.category == "became_required" and c.path == "$.note" for c in changes)


def test_nested_object_field_change() -> None:
    old = {"user": {"name": "Alice"}}
    new = {"user": {"name": "Alice", "email": "a@x.com"}}

    changes = diff_payloads(old, new)

    assert any(c.path == "$.user.email" and c.category == "added_field" for c in changes)


def test_array_item_shape_change() -> None:
    old = {"users": [{"id": 1, "name": "A"}]}
    new = {"users": [{"id": 1, "name": "A", "email": "a@x.com"}]}

    changes = diff_payloads(old, new)

    assert any(c.path == "$.users[].email" for c in changes)


def test_type_changed_stops_recursion_into_children() -> None:
    old = {"data": {"a": 1}}
    new = {"data": [1, 2, 3]}

    changes = diff_payloads(old, new)

    assert _categories(changes) == ["type_changed"]
    assert changes[0].path == "$.data"


def test_diff_schemas_directly() -> None:
    old_schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    new_schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": []}

    changes = diff_schemas(old_schema, new_schema)

    assert len(changes) == 1
    assert changes[0].category == "became_optional"


def test_infer_schema_from_samples_matches_diff_expectations() -> None:
    schema = infer_schema_from_samples([{"a": 1}, {"a": 2, "b": "x"}])

    assert schema["required"] == ["a"]
    assert set(schema["properties"]) == {"a", "b"}
