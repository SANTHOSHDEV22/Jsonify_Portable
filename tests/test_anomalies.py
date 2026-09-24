"""Tests for anomaly detection (profile-driven deviation checks)."""

from __future__ import annotations

from jsonify.core.anomalies import detect_anomalies


def _categories(data) -> set[str]:
    return {a.category for a in detect_anomalies(data)}


def test_type_inconsistency() -> None:
    payload = [{"age": 25}, {"age": 27}, {"age": "unknown"}]

    anomalies = detect_anomalies(payload)

    assert len(anomalies) == 1
    assert anomalies[0].category == "type_inconsistency"
    assert "age" in anomalies[0].path


def test_null_concentration_above_threshold() -> None:
    payload = [{"email": "a@x.com"}, {"email": None}, {"email": None}, {"email": None}]

    anomalies = detect_anomalies(payload, null_rate_threshold=0.5)

    assert any(a.category == "null_concentration" for a in anomalies)


def test_null_concentration_below_threshold_not_flagged() -> None:
    payload = [{"email": f"{i}@x.com"} for i in range(9)] + [{"email": None}]

    assert "null_concentration" not in _categories(payload)


def test_unexpected_rare_field() -> None:
    payload = [{"id": i} for i in range(19)] + [{"id": 19, "debugInfo": "x"}]

    anomalies = detect_anomalies(payload)

    rare = [a for a in anomalies if a.category == "unexpected_field"]
    assert len(rare) == 1
    assert "debugInfo" in rare[0].path


def test_common_field_not_flagged_as_rare() -> None:
    payload = [{"id": i, "name": f"n{i}"} for i in range(10)]

    assert "unexpected_field" not in _categories(payload)


def test_duplicate_identity_values() -> None:
    payload = [{"id": 101}, {"id": 102}, {"id": 101}]

    anomalies = detect_anomalies(payload)

    dup = [a for a in anomalies if a.category == "duplicate_identity"]
    assert len(dup) == 1
    assert "id" in dup[0].path
    assert "101" in dup[0].message


def test_duplicate_identity_with_suffix_field_name() -> None:
    payload = [{"user_id": 5}, {"user_id": 5}]

    anomalies = detect_anomalies(payload)

    assert any(a.category == "duplicate_identity" and "user_id" in a.path for a in anomalies)


def test_unique_identities_not_flagged() -> None:
    payload = [{"id": 1}, {"id": 2}, {"id": 3}]

    assert "duplicate_identity" not in _categories(payload)


def test_clean_array_has_no_anomalies() -> None:
    payload = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    assert detect_anomalies(payload) == []


def test_arrays_with_fewer_than_two_items_are_skipped() -> None:
    assert detect_anomalies([{"id": 1, "extra": "x"}]) == []


def test_no_arrays_of_objects_returns_no_anomalies() -> None:
    assert detect_anomalies({"a": 1, "b": [1, 2, 3]}) == []
