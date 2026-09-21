"""Heuristic JSON analyzer.

Surfaces things worth a second look that a validator wouldn't catch,
since they're all individually valid JSON: duplicate array entries,
arrays whose objects don't share a consistent shape, mixed-type arrays,
empty values, and unusually deep nesting.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from jsonify.core.models import JSONValue

DEFAULT_DEPTH_THRESHOLD = 15


@dataclass(slots=True)
class AnalyzerFinding:
    """One thing the analyzer noticed."""

    category: str
    message: str
    path: str


@dataclass(slots=True)
class AnalyzerReport:
    """All findings from one analysis pass."""

    findings: list[AnalyzerFinding] = field(default_factory=list)

    def by_category(self) -> dict[str, list[AnalyzerFinding]]:
        grouped: dict[str, list[AnalyzerFinding]] = {}
        for finding in self.findings:
            grouped.setdefault(finding.category, []).append(finding)
        return grouped


def _type_name(value: JSONValue) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


def analyze_json(
    data: JSONValue,
    *,
    depth_threshold: int = DEFAULT_DEPTH_THRESHOLD,
) -> AnalyzerReport:
    """Run every heuristic check over ``data`` and return the findings."""

    findings: list[AnalyzerFinding] = []

    _check_empty_and_depth(data, path="$", depth=0, threshold=depth_threshold, findings=findings)
    _check_arrays(data, path="$", findings=findings)

    return AnalyzerReport(findings=findings)


def _check_empty_and_depth(
    node: JSONValue,
    *,
    path: str,
    depth: int,
    threshold: int,
    findings: list[AnalyzerFinding],
) -> None:
    if depth == threshold:
        findings.append(
            AnalyzerFinding(
                category="deep_nesting",
                message=f"Nesting exceeds {threshold} levels here.",
                path=path,
            )
        )

    if node == "" or node == [] or node == {}:
        kind = _type_name(node)
        findings.append(
            AnalyzerFinding(
                category="empty_value",
                message=f"Empty {kind} value.",
                path=path,
            )
        )
        return

    if isinstance(node, dict):
        for key, value in node.items():
            _check_empty_and_depth(
                value,
                path=f"{path}.{key}",
                depth=depth + 1,
                threshold=threshold,
                findings=findings,
            )
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _check_empty_and_depth(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
                threshold=threshold,
                findings=findings,
            )


def _check_arrays(node: JSONValue, *, path: str, findings: list[AnalyzerFinding]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _check_arrays(value, path=f"{path}.{key}", findings=findings)
        return

    if not isinstance(node, list):
        return

    for index, item in enumerate(node):
        _check_arrays(item, path=f"{path}[{index}]", findings=findings)

    _check_duplicate_entries(node, path=path, findings=findings)
    _check_inconsistent_object_shapes(node, path=path, findings=findings)
    _check_mixed_primitive_types(node, path=path, findings=findings)


def _check_duplicate_entries(
    items: list[JSONValue], *, path: str, findings: list[AnalyzerFinding]
) -> None:
    seen: dict[str, list[int]] = {}

    for index, item in enumerate(items):
        if not isinstance(item, dict | list):
            continue
        signature = json.dumps(item, sort_keys=True, ensure_ascii=False)
        seen.setdefault(signature, []).append(index)

    for indices in seen.values():
        if len(indices) > 1:
            index_list = ", ".join(str(i) for i in indices)
            findings.append(
                AnalyzerFinding(
                    category="duplicate_entry",
                    message=f"{len(indices)} array entries are identical (indices {index_list}).",
                    path=path,
                )
            )


def _check_inconsistent_object_shapes(
    items: list[JSONValue], *, path: str, findings: list[AnalyzerFinding]
) -> None:
    object_items = [(i, item) for i, item in enumerate(items) if isinstance(item, dict)]
    if len(object_items) < 2:
        return

    signatures = Counter(frozenset(item.keys()) for _, item in object_items)
    most_common_signature, _ = signatures.most_common(1)[0]

    if len(signatures) <= 1:
        return

    outliers = [i for i, item in object_items if frozenset(item.keys()) != most_common_signature]

    if outliers:
        index_list = ", ".join(str(i) for i in outliers)
        findings.append(
            AnalyzerFinding(
                category="inconsistent_shape",
                message=(
                    f"{len(outliers)} object(s) have a different set of keys than "
                    f"the rest of this array (indices {index_list})."
                ),
                path=path,
            )
        )


def _check_mixed_primitive_types(
    items: list[JSONValue], *, path: str, findings: list[AnalyzerFinding]
) -> None:
    primitive_types = {_type_name(item) for item in items if not isinstance(item, dict | list)}

    if len(primitive_types) > 1:
        type_list = ", ".join(sorted(primitive_types))
        findings.append(
            AnalyzerFinding(
                category="mixed_types",
                message=f"Array mixes primitive types: {type_list}.",
                path=path,
            )
        )
