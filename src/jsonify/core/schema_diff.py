"""Schema evolution: classify how a JSON shape changed between two versions.

Unlike ``core.diff`` (which compares two *values*) and
``core.breaking_changes`` (which classifies a value diff using a schema),
this compares two *schemas* directly — typically ones inferred from "before"
and "after" sample payloads via ``core.schema_inference`` — and reports
added/removed fields, type changes, and required ⇄ optional transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonify.core.models import JSONValue
from jsonify.core.schema_inference import infer_schema, infer_schema_from_samples

_CATEGORY_LABELS = {
    "added_field": "Added field",
    "removed_field": "Removed field",
    "type_changed": "Type changed",
    "became_required": "Became required",
    "became_optional": "Became optional",
}


@dataclass(frozen=True, slots=True)
class SchemaChange:
    """One classified difference between an old and a new schema."""

    category: str
    path: str
    detail: str

    @property
    def label(self) -> str:
        return _CATEGORY_LABELS.get(self.category, self.category)


def diff_schemas(old_schema: dict[str, Any], new_schema: dict[str, Any]) -> list[SchemaChange]:
    """Classify the differences between two JSON Schemas."""

    changes: list[SchemaChange] = []
    _diff_node(old_schema, new_schema, "$", changes)
    return changes


def diff_payloads(old_sample: JSONValue, new_sample: JSONValue) -> list[SchemaChange]:
    """Infer a schema from each sample, then diff those schemas."""

    return diff_schemas(infer_schema(old_sample), infer_schema(new_sample))


def diff_sample_sets(
    old_samples: list[JSONValue], new_samples: list[JSONValue]
) -> list[SchemaChange]:
    """Like :func:`diff_payloads`, but each side is inferred from several
    independent samples (e.g. several "v1" responses vs. several "v2" ones)."""

    return diff_schemas(
        infer_schema_from_samples(old_samples), infer_schema_from_samples(new_samples)
    )


def _diff_node(
    old: dict[str, Any], new: dict[str, Any], path: str, changes: list[SchemaChange]
) -> None:
    old_type = old.get("type")
    new_type = new.get("type")

    if old_type != new_type and old_type is not None and new_type is not None:
        changes.append(
            SchemaChange("type_changed", path, f"{_type_text(old_type)} -> {_type_text(new_type)}")
        )
        return  # shapes are unrelated now; comparing their properties would be noise

    if old_type == "object" or new_type == "object":
        _diff_object(old, new, path, changes)

    if old_type == "array" or new_type == "array":
        old_items = old.get("items")
        new_items = new.get("items")
        if isinstance(old_items, dict) and isinstance(new_items, dict) and old_items and new_items:
            _diff_node(old_items, new_items, f"{path}[]", changes)


def _diff_object(
    old: dict[str, Any], new: dict[str, Any], path: str, changes: list[SchemaChange]
) -> None:
    old_props: dict[str, Any] = old.get("properties", {})
    new_props: dict[str, Any] = new.get("properties", {})
    old_required = set(old.get("required", []))
    new_required = set(new.get("required", []))

    for name in sorted(set(old_props) - set(new_props)):
        old_type = _type_text(old_props[name].get("type"))
        changes.append(SchemaChange("removed_field", f"{path}.{name}", f"Was {old_type}."))

    for name in sorted(set(new_props) - set(old_props)):
        changes.append(
            SchemaChange(
                "added_field",
                f"{path}.{name}",
                f"Now {_type_text(new_props[name].get('type'))}"
                + (" (required)." if name in new_required else " (optional)."),
            )
        )

    for name in sorted(set(old_props) & set(new_props)):
        child_path = f"{path}.{name}"

        if name in old_required and name not in new_required:
            changes.append(SchemaChange("became_optional", child_path, "No longer required."))
        elif name not in old_required and name in new_required:
            changes.append(SchemaChange("became_required", child_path, "Now required."))

        _diff_node(old_props[name], new_props[name], child_path, changes)


def _type_text(type_value: Any) -> str:
    if isinstance(type_value, list):
        return " | ".join(str(t) for t in type_value)
    return str(type_value)
