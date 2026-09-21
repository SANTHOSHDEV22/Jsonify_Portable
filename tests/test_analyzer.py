"""Tests for the heuristic JSON analyzer."""

from __future__ import annotations

from jsonify.core.analyzer import analyze_json


def test_analyzer_flags_empty_values() -> None:
    report = analyze_json({"a": "", "b": [], "c": {}})

    categories = [f.category for f in report.findings]
    assert categories.count("empty_value") == 3


def test_analyzer_flags_deep_nesting() -> None:
    payload = {"a": {}}
    node = payload["a"]
    for _ in range(20):
        node["child"] = {}
        node = node["child"]

    report = analyze_json(payload, depth_threshold=5)

    assert any(f.category == "deep_nesting" for f in report.findings)


def test_analyzer_flags_duplicate_array_entries() -> None:
    payload = [{"id": 1}, {"id": 1}, {"id": 2}]

    report = analyze_json(payload)

    duplicate_findings = [f for f in report.findings if f.category == "duplicate_entry"]
    assert len(duplicate_findings) == 1
    assert "0" in duplicate_findings[0].message and "1" in duplicate_findings[0].message


def test_analyzer_flags_inconsistent_object_shapes() -> None:
    payload = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}, {"id": 3}]

    report = analyze_json(payload)

    findings = [f for f in report.findings if f.category == "inconsistent_shape"]
    assert len(findings) == 1


def test_analyzer_flags_mixed_primitive_types() -> None:
    payload = [1, "two", True]

    report = analyze_json(payload)

    findings = [f for f in report.findings if f.category == "mixed_types"]
    assert len(findings) == 1


def test_analyzer_clean_payload_has_no_findings() -> None:
    payload = {"users": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}

    report = analyze_json(payload)

    assert report.findings == []


def test_analyzer_by_category_groups_findings() -> None:
    payload = {"a": ""}
    report = analyze_json(payload)

    grouped = report.by_category()
    assert "empty_value" in grouped
    assert len(grouped["empty_value"]) == 1
