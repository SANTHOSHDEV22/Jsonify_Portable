"""Tests for Markdown diff-report rendering."""

from __future__ import annotations

from jsonify.core.diff import DiffType, JsonDiff
from jsonify.core.diff_report import render_diff_report


def test_report_no_differences() -> None:
    report = render_diff_report([])
    assert "No differences found" in report


def test_report_includes_summary_counts() -> None:
    diffs = [
        JsonDiff(diff_type=DiffType.ADDED, path="$.b", new_value=2),
        JsonDiff(diff_type=DiffType.REMOVED, path="$.a", old_value=1),
    ]

    report = render_diff_report(diffs)

    assert "2 difference(s)" in report
    assert "1 added" in report
    assert "1 removed" in report


def test_report_includes_table_rows() -> None:
    diffs = [JsonDiff(diff_type=DiffType.CHANGED, path="$.status", old_value="a", new_value="b")]

    report = render_diff_report(diffs)

    assert "$.status" in report
    assert "Changed" in report


def test_report_custom_title() -> None:
    report = render_diff_report([], title="My Report")
    assert report.startswith("# My Report")
