"""Render a list of JSON diffs as a human-readable report."""

from __future__ import annotations

import json

from jsonify.core.diff import DiffType, JsonDiff
from jsonify.core.models import JSONValue

_LABELS = {
    DiffType.ADDED: "Added",
    DiffType.REMOVED: "Removed",
    DiffType.CHANGED: "Changed",
    DiffType.TYPE_CHANGED: "Type Changed",
}


def render_diff_report(differences: list[JsonDiff], *, title: str = "JSON Diff Report") -> str:
    """Render diffs as a Markdown report, grouped by change type."""

    if not differences:
        return f"# {title}\n\nNo differences found — the documents are identical.\n"

    counts = {diff_type: 0 for diff_type in DiffType}
    for diff in differences:
        counts[diff.diff_type] += 1

    lines = [
        f"# {title}",
        "",
        f"**{len(differences)} difference(s)** — "
        + ", ".join(f"{counts[t]} {_LABELS[t].lower()}" for t in DiffType if counts[t]),
        "",
        "| Change | Path | Old Value | New Value |",
        "|---|---|---|---|",
    ]

    for diff in differences:
        old_text = "—" if diff.diff_type == DiffType.ADDED else _cell(diff.old_value)
        new_text = "—" if diff.diff_type == DiffType.REMOVED else _cell(diff.new_value)
        lines.append(f"| {_LABELS[diff.diff_type]} | `{diff.path}` | {old_text} | {new_text} |")

    lines.append("")
    return "\n".join(lines)


def _cell(value: JSONValue) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, dict | list):
        return f"`{json.dumps(value, ensure_ascii=False, separators=(',', ':'))}`"
    return f"`{value!r}`"
