"""Tests for JSON profiling."""

from __future__ import annotations

from jsonify.core.profiling import profile_json


def test_profile_root_type_and_stats() -> None:
    profile = profile_json({"a": 1, "b": "x"})

    assert profile.root_type == "object"
    assert profile.stats["objects"] == 1
    assert profile.stats["strings"] == 1
    assert profile.stats["numbers"] == 1


def test_profile_finds_array_of_objects_and_field_stats() -> None:
    payload = {
        "users": [
            {"id": 1, "name": "Alice", "email": "a@example.com"},
            {"id": 2, "name": "Bob", "email": None},
        ]
    }

    profile = profile_json(payload)

    assert len(profile.arrays) == 1
    array = profile.arrays[0]
    assert array.path == "$.users"
    assert array.item_count == 2

    id_field = array.fields["id"]
    assert id_field.occurrences == 2
    assert id_field.is_required
    assert id_field.types == ["integer"]
    assert id_field.unique_values == 2

    email_field = array.fields["email"]
    assert email_field.null_count == 1
    assert email_field.null_rate == 0.5
    assert not email_field.is_required  # present but null on one item


def test_profile_optional_field_across_items() -> None:
    payload = [{"id": 1, "name": "Alice"}, {"id": 2}]

    profile = profile_json(payload)

    name_field = profile.arrays[0].fields["name"]
    assert name_field.occurrences == 1
    assert name_field.occurrence_rate == 0.5
    assert not name_field.is_required


def test_profile_mixed_type_field() -> None:
    payload = [{"age": 25}, {"age": "unknown"}]

    profile = profile_json(payload)

    age_field = profile.arrays[0].fields["age"]
    assert set(age_field.types) == {"integer", "string"}


def test_profile_nested_arrays_of_objects_both_profiled() -> None:
    payload = {
        "departments": [
            {"name": "Eng", "employees": [{"id": 1}, {"id": 2}]},
        ]
    }

    profile = profile_json(payload)
    paths = {array.path for array in profile.arrays}

    assert "$.departments" in paths
    assert "$.departments[0].employees" in paths


def test_profile_array_of_scalars_is_not_profiled() -> None:
    profile = profile_json({"tags": ["a", "b", "c"]})

    assert profile.arrays == []


def test_profile_unique_values_counts_container_values() -> None:
    payload = [{"tags": ["x", "y"]}, {"tags": ["x", "y"]}, {"tags": ["z"]}]

    profile = profile_json(payload)

    assert profile.arrays[0].fields["tags"].unique_values == 2


def test_summary_text_includes_field_table() -> None:
    payload = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    text = profile_json(payload).summary_text()

    assert "$" in text
    assert "id" in text
    assert "name" in text
    assert "required" in text
