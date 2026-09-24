"""Anomaly detection: profile the data, then flag deviations from it.

Complements ``core.analyzer`` (which looks at raw structure — duplicate
entries, mixed types, empty values) with *field-level* checks that only
make sense once a :class:`~jsonify.core.profiling.JsonProfile` exists:
a field whose type disagrees with the rest of the array, a field that's
null far more often than usual, a field only a few outlier items have,
and duplicate values in an identity-like field (e.g. ``id``).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass

from jsonify.core.models import JSONValue
from jsonify.core.profiling import ArrayProfile, JsonProfile, profile_json

DEFAULT_NULL_RATE_THRESHOLD = 0.3
DEFAULT_RARE_FIELD_THRESHOLD = 0.1


@dataclass(frozen=True, slots=True)
class Anomaly:
    """One deviation from the array's typical shape."""

    category: str
    path: str
    message: str


def detect_anomalies(
    data: JSONValue,
    *,
    null_rate_threshold: float = DEFAULT_NULL_RATE_THRESHOLD,
    rare_field_threshold: float = DEFAULT_RARE_FIELD_THRESHOLD,
) -> list[Anomaly]:
    """Profile ``data`` and return every anomaly found in its arrays of objects."""

    return detect_anomalies_from_profile(
        profile_json(data),
        null_rate_threshold=null_rate_threshold,
        rare_field_threshold=rare_field_threshold,
    )


def detect_anomalies_from_profile(
    profile: JsonProfile,
    *,
    null_rate_threshold: float = DEFAULT_NULL_RATE_THRESHOLD,
    rare_field_threshold: float = DEFAULT_RARE_FIELD_THRESHOLD,
) -> list[Anomaly]:
    """Same as :func:`detect_anomalies`, reusing an already-built profile."""

    anomalies: list[Anomaly] = []

    for array in profile.arrays:
        if array.item_count < 2:
            continue

        _check_type_inconsistency(array, anomalies)
        _check_null_concentration(array, null_rate_threshold, anomalies)
        _check_rare_fields(array, rare_field_threshold, anomalies)
        _check_duplicate_identities(array, anomalies)

    return anomalies


def _check_type_inconsistency(array: ArrayProfile, anomalies: list[Anomaly]) -> None:
    for name, field in sorted(array.fields.items()):
        non_null_types = {t for t in field.type_counts if t != "null"}
        if len(non_null_types) > 1:
            breakdown = ", ".join(f"{t}: {count}" for t, count in sorted(field.type_counts.items()))
            anomalies.append(
                Anomaly(
                    category="type_inconsistency",
                    path=f"{array.path}[*].{name}",
                    message=f"Mixed types for '{name}' ({breakdown}).",
                )
            )


def _check_null_concentration(
    array: ArrayProfile, threshold: float, anomalies: list[Anomaly]
) -> None:
    for name, field in sorted(array.fields.items()):
        if field.null_rate >= threshold and field.null_count > 0:
            anomalies.append(
                Anomaly(
                    category="null_concentration",
                    path=f"{array.path}[*].{name}",
                    message=f"'{name}' is null in {field.null_rate:.0%} of items "
                    f"({field.null_count}/{field.total_items}).",
                )
            )


def _check_rare_fields(array: ArrayProfile, threshold: float, anomalies: list[Anomaly]) -> None:
    if array.item_count < 5:
        return  # too few items for "rare" to mean anything

    for name, field in sorted(array.fields.items()):
        if 0 < field.occurrence_rate < threshold:
            anomalies.append(
                Anomaly(
                    category="unexpected_field",
                    path=f"{array.path}[*].{name}",
                    message=f"'{name}' appears on only {field.occurrences}/{field.total_items} "
                    "items — most items don't have it.",
                )
            )


def _check_duplicate_identities(array: ArrayProfile, anomalies: list[Anomaly]) -> None:
    for name, values in sorted(array.identity_values.items()):
        counts = Counter(_hashable(v) for v in values if v is not None)
        duplicates = {value: count for value, count in counts.items() if count > 1}

        if duplicates:
            examples = ", ".join(
                f"{value!r} x{count}" for value, count in list(duplicates.items())[:5]
            )
            anomalies.append(
                Anomaly(
                    category="duplicate_identity",
                    path=f"{array.path}[*].{name}",
                    message=f"Duplicate '{name}' value(s): {examples}.",
                )
            )


def _hashable(value: JSONValue) -> object:
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value
