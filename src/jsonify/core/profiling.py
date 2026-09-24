"""JSON profiling: structural stats plus per-field statistics for arrays
of objects (the common "list of records" shape of API payloads).

This is what feeds the Anomaly Detector (``core/anomalies.py``) and the
AI structure-summary prompt (``core/ai_prompts.py``) — both consume a
:class:`JsonProfile` rather than re-walking the payload themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jsonify.core.models import JSONValue
from jsonify.core.pointer import PathSegment, to_json_path
from jsonify.core.traversal import calculate_json_stats


def _type_name(value: JSONValue) -> str:
    """Distinguishes integer/number (matches ``core.schema_inference``'s
    convention, since profiles and inferred schemas describe the same
    shape)."""

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
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


@dataclass(slots=True)
class FieldProfile:
    """Statistics for one field across every object in an array."""

    name: str
    occurrences: int  # objects that had this key at all
    total_items: int  # objects in the array (occurrences may be < this)
    type_counts: dict[str, int] = field(default_factory=dict)
    null_count: int = 0
    unique_values: int = 0
    example: JSONValue = None

    @property
    def null_rate(self) -> float:
        return self.null_count / self.total_items if self.total_items else 0.0

    @property
    def occurrence_rate(self) -> float:
        return self.occurrences / self.total_items if self.total_items else 0.0

    @property
    def types(self) -> list[str]:
        return sorted(self.type_counts, key=lambda t: (-self.type_counts[t], t))

    @property
    def is_required(self) -> bool:
        """Present, non-null, on every item — a reasonable "required" signal."""

        return self.occurrences == self.total_items and self.null_count == 0


#: Field names (or suffixes, as "_id") treated as identity-like when
#: capturing raw values for duplicate-value checks (see ``core.anomalies``).
IDENTITY_FIELD_HINTS = ("id", "uuid", "guid", "key", "code")


@dataclass(slots=True)
class ArrayProfile:
    """Field-level profile of one array of objects found in the payload."""

    path_segments: tuple[PathSegment, ...]
    item_count: int
    fields: dict[str, FieldProfile] = field(default_factory=dict)
    #: Raw values for identity-like fields only (kept small on purpose —
    #: everything else is aggregated stats, not copies of the data).
    identity_values: dict[str, list[JSONValue]] = field(default_factory=dict)

    @property
    def path(self) -> str:
        return to_json_path(list(self.path_segments))


@dataclass(slots=True)
class JsonProfile:
    """A full profile of one JSON document."""

    root_type: str
    stats: dict[str, int]
    arrays: list[ArrayProfile] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        """A short, human-readable summary (also used in AI prompts)."""

        lines = [
            f"Root type: {self.root_type}",
            f"Total nodes: {self.stats['objects'] + self.stats['arrays'] + self.stats['leaves']:,}",
            f"Objects: {self.stats['objects']:,}  Arrays: {self.stats['arrays']:,}",
            f"Strings: {self.stats['strings']:,}  Numbers: {self.stats['numbers']:,}  "
            f"Booleans: {self.stats['booleans']:,}  Nulls: {self.stats['nulls']:,}",
            f"Unique keys: {self.stats['keys']:,}  Max depth: {self.stats['max_depth']}",
        ]

        for array in self.arrays:
            lines.append(f"\n{array.path} — {array.item_count} item(s):")
            for name, profile in sorted(array.fields.items()):
                required = "required" if profile.is_required else "optional"
                types = "|".join(profile.types)
                lines.append(
                    f"  {name:<24} {types:<12} {required:<9} "
                    f"null={profile.null_rate:.0%} unique={profile.unique_values}"
                )

        return lines

    def summary_text(self) -> str:
        return "\n".join(self.summary_lines())


def profile_json(data: JSONValue) -> JsonProfile:
    """Build a full profile of ``data``: overall stats plus a per-field
    breakdown of every array of objects found anywhere in the document."""

    stats = calculate_json_stats(data)
    arrays: list[ArrayProfile] = []
    _find_arrays(data, (), arrays)

    return JsonProfile(root_type=_type_name(data), stats=stats, arrays=arrays)


def _find_arrays(
    node: JSONValue,
    segments: tuple[PathSegment, ...],
    arrays: list[ArrayProfile],
) -> None:
    if isinstance(node, dict):
        for key, child in node.items():
            _find_arrays(child, (*segments, key), arrays)
        return

    if not isinstance(node, list):
        return

    object_items = [item for item in node if isinstance(item, dict)]
    if object_items:
        arrays.append(_profile_array(segments, node, object_items))

    for index, item in enumerate(node):
        _find_arrays(item, (*segments, index), arrays)


def _profile_array(
    segments: tuple[PathSegment, ...],
    all_items: list[JSONValue],
    object_items: list[dict[str, JSONValue]],
) -> ArrayProfile:
    total = len(all_items)
    fields: dict[str, FieldProfile] = {}

    for item in object_items:
        for name, value in item.items():
            profile = fields.setdefault(
                name, FieldProfile(name=name, occurrences=0, total_items=total)
            )
            profile.occurrences += 1

            type_name = _type_name(value)
            profile.type_counts[type_name] = profile.type_counts.get(type_name, 0) + 1

            if value is None:
                profile.null_count += 1
            if profile.example is None and value is not None:
                profile.example = value

    identity_values: dict[str, list[JSONValue]] = {}
    for name, values in _collect_values(object_items).items():
        fields[name].unique_values = len({_hashable(v) for v in values})
        if _looks_like_identity(name):
            identity_values[name] = values

    return ArrayProfile(
        path_segments=segments,
        item_count=total,
        fields=fields,
        identity_values=identity_values,
    )


def _looks_like_identity(name: str) -> bool:
    lowered = name.lower()
    return lowered in IDENTITY_FIELD_HINTS or any(
        lowered.endswith(f"_{hint}") for hint in IDENTITY_FIELD_HINTS
    )


def _collect_values(items: list[dict[str, JSONValue]]) -> dict[str, list[JSONValue]]:
    collected: dict[str, list[JSONValue]] = {}
    for item in items:
        for name, value in item.items():
            collected.setdefault(name, []).append(value)
    return collected


def _hashable(value: JSONValue) -> object:
    """Make container values hashable enough for a uniqueness count."""

    if isinstance(value, dict | list):
        import json

        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value
