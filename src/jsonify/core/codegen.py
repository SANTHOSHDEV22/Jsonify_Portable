"""Generate typed model source code from a sample JSON payload.

Inspects a sample payload once to build a small set of ``ClassModel``
objects (one per distinct JSON object shape encountered, including
nested ones), then renders that same model into each target language.
Arrays of objects are inferred from the *union* of all their items, so a
field that's only present on some array entries still shows up (as
optional) rather than being silently dropped.
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass, field

from jsonify.core.models import JSONValue

SUPPORTED_LANGUAGES = ("csharp", "java", "typescript", "python", "go", "kotlin")


@dataclass(slots=True)
class TypeRef:
    """A field's inferred type: a JSON-ish kind, plus extra info for
    object/array kinds."""

    kind: str  # string|integer|number|boolean|null|any|object|array
    class_name: str = ""
    item: TypeRef | None = None


@dataclass(slots=True)
class ClassModel:
    """One generated class/type: its name and (field name, type, nullable)."""

    name: str
    fields: list[tuple[str, TypeRef, bool]] = field(default_factory=list)


def infer_classes(
    payload: JSONValue, *, root_name: str = "Root"
) -> tuple[list[ClassModel], TypeRef]:
    """Infer classes from a sample payload.

    Returns the discovered classes (in first-seen order) and the type of
    the root value itself, so callers can tell whether the payload's top
    level is an object, an array, or a bare scalar.
    """

    classes: dict[str, ClassModel] = {}
    root_type = _infer(payload, root_name, classes)
    return list(classes.values()), root_type


def _infer(value: JSONValue, suggested_name: str, classes: dict[str, ClassModel]) -> TypeRef:
    if value is None:
        return TypeRef("null")
    if isinstance(value, bool):
        return TypeRef("boolean")
    if isinstance(value, int):
        return TypeRef("integer")
    if isinstance(value, float):
        return TypeRef("number")
    if isinstance(value, str):
        return TypeRef("string")

    if isinstance(value, list):
        if not value:
            return TypeRef("array", item=TypeRef("any"))

        if all(isinstance(item, dict) for item in value):
            merged = _merge_dicts(value)
            item_type = _infer(merged, suggested_name, classes)
        else:
            item_type = _infer(value[0], suggested_name, classes)

        return TypeRef("array", item=item_type)

    if isinstance(value, dict):
        class_name = _dedupe_name(_pascal_case(suggested_name), classes)
        fields: list[tuple[str, TypeRef, bool]] = []

        # Reserve the name before recursing so a field that refers back
        # to this shape doesn't collide with it.
        classes[class_name] = ClassModel(class_name, fields)

        for key, item_value in value.items():
            field_type = _infer(item_value, key, classes)
            fields.append((key, field_type, item_value is None))

        return TypeRef("object", class_name=class_name)

    return TypeRef("any")


def _merge_dicts(items: list[JSONValue]) -> dict[str, JSONValue]:
    """Union all keys across a list of objects (first non-null value wins,
    used only to infer a representative shape)."""

    merged: dict[str, JSONValue] = {}
    for item in items:
        if isinstance(item, dict):
            for key, value in item.items():
                if key not in merged or merged[key] is None:
                    merged[key] = value
    return merged


def _item_of(type_ref: TypeRef) -> TypeRef:
    """Return an array type's item type (``any`` if it has none)."""

    return type_ref.item if type_ref.item is not None else TypeRef("any")


def _pascal_case(name: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", name)
    return "".join(part[:1].upper() + part[1:] for part in parts if part) or "Item"


def _dedupe_name(name: str, classes: dict[str, ClassModel]) -> str:
    if name not in classes:
        return name
    index = 2
    while f"{name}{index}" in classes:
        index += 1
    return f"{name}{index}"


# ---------------------------------------------------------------------
# C#
# ---------------------------------------------------------------------

_CSHARP_TYPES = {
    "string": "string",
    "integer": "int",
    "number": "double",
    "boolean": "bool",
    "null": "object",
    "any": "object",
}


def _csharp_type(type_ref: TypeRef, nullable: bool) -> str:
    if type_ref.kind == "object":
        return type_ref.class_name
    if type_ref.kind == "array":
        return f"List<{_csharp_type(_item_of(type_ref), False)}>"
    base = _CSHARP_TYPES.get(type_ref.kind, "object")
    if nullable and base in ("int", "double", "bool"):
        return f"{base}?"
    return base


def generate_csharp(classes: list[ClassModel]) -> str:
    """Render C# classes with auto-properties."""

    blocks = []
    for cls in classes:
        lines = [f"public class {cls.name}", "{"]
        for field_name, type_ref, nullable in cls.fields:
            lines.append(
                f"    public {_csharp_type(type_ref, nullable)} "
                f"{_pascal_case(field_name)} {{ get; set; }}"
            )
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------

_JAVA_TYPES = {
    "string": "String",
    "integer": "int",
    "number": "double",
    "boolean": "boolean",
    "null": "Object",
    "any": "Object",
}


def _java_type(type_ref: TypeRef) -> str:
    if type_ref.kind == "object":
        return type_ref.class_name
    if type_ref.kind == "array":
        return f"List<{_java_type(_item_of(type_ref))}>"
    return _JAVA_TYPES.get(type_ref.kind, "Object")


def generate_java(classes: list[ClassModel]) -> str:
    """Render Java POJOs with private fields and getters/setters."""

    blocks = []
    for cls in classes:
        lines = [f"public class {cls.name} {{"]
        for field_name, type_ref, _nullable in cls.fields:
            java_field = _camel_case(field_name)
            lines.append(f"    private {_java_type(type_ref)} {java_field};")
        lines.append("")
        for field_name, type_ref, _nullable in cls.fields:
            java_field = _camel_case(field_name)
            capitalized = java_field[:1].upper() + java_field[1:]
            java_type = _java_type(type_ref)
            lines.append(f"    public {java_type} get{capitalized}() {{ return {java_field}; }}")
            lines.append(
                f"    public void set{capitalized}({java_type} {java_field}) "
                f"{{ this.{java_field} = {java_field}; }}"
            )
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------
# TypeScript
# ---------------------------------------------------------------------

_TS_TYPES = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "null": "null",
    "any": "any",
}


def _ts_type(type_ref: TypeRef) -> str:
    if type_ref.kind == "object":
        return type_ref.class_name
    if type_ref.kind == "array":
        return f"{_ts_type(_item_of(type_ref))}[]"
    return _TS_TYPES.get(type_ref.kind, "any")


def generate_typescript(classes: list[ClassModel]) -> str:
    """Render TypeScript interfaces."""

    blocks = []
    for cls in classes:
        lines = [f"export interface {cls.name} {{"]
        for field_name, type_ref, nullable in cls.fields:
            optional = "?" if nullable else ""
            lines.append(f"  {field_name}{optional}: {_ts_type(type_ref)};")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------

_PY_TYPES = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "null": "None",
    "any": "Any",
}


def _python_type(type_ref: TypeRef, nullable: bool) -> str:
    if type_ref.kind == "object":
        base = type_ref.class_name
    elif type_ref.kind == "array":
        base = f"list[{_python_type(_item_of(type_ref), False)}]"
    else:
        base = _PY_TYPES.get(type_ref.kind, "Any")
    return f"{base} | None" if nullable and base != "None" else base


def generate_python(classes: list[ClassModel]) -> str:
    """Render Python ``@dataclass`` models."""

    blocks = ["from __future__ import annotations", "", "from dataclasses import dataclass"]
    for cls in classes:
        blocks.append("")
        blocks.append("")
        blocks.append("@dataclass")
        blocks.append(f"class {cls.name}:")
        if not cls.fields:
            blocks.append("    pass")
        for field_name, type_ref, nullable in cls.fields:
            safe_name = f"{field_name}_" if keyword.iskeyword(field_name) else field_name
            blocks.append(f"    {safe_name}: {_python_type(type_ref, nullable)}")
    return "\n".join(blocks)


# ---------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------

_GO_TYPES = {
    "string": "string",
    "integer": "int",
    "number": "float64",
    "boolean": "bool",
    "null": "interface{}",
    "any": "interface{}",
}


def _go_type(type_ref: TypeRef) -> str:
    if type_ref.kind == "object":
        return type_ref.class_name
    if type_ref.kind == "array":
        return f"[]{_go_type(_item_of(type_ref))}"
    return _GO_TYPES.get(type_ref.kind, "interface{}")


def generate_go(classes: list[ClassModel]) -> str:
    """Render Go structs with JSON tags."""

    blocks = []
    for cls in classes:
        lines = [f"type {cls.name} struct {{"]
        rows = [
            (_pascal_case(field_name), _go_type(type_ref), field_name)
            for field_name, type_ref, _nullable in cls.fields
        ]
        name_width = max((len(r[0]) for r in rows), default=0)
        type_width = max((len(r[1]) for r in rows), default=0)
        for go_name, go_type, original_name in rows:
            lines.append(
                f"    {go_name.ljust(name_width)} {go_type.ljust(type_width)} "
                f'`json:"{original_name}"`'
            )
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------
# Kotlin
# ---------------------------------------------------------------------

_KOTLIN_TYPES = {
    "string": "String",
    "integer": "Int",
    "number": "Double",
    "boolean": "Boolean",
    "null": "Any?",
    "any": "Any",
}


def _kotlin_type(type_ref: TypeRef, nullable: bool) -> str:
    if type_ref.kind == "object":
        base = type_ref.class_name
    elif type_ref.kind == "array":
        base = f"List<{_kotlin_type(_item_of(type_ref), False)}>"
    else:
        base = _KOTLIN_TYPES.get(type_ref.kind, "Any")
    return f"{base}?" if nullable and not base.endswith("?") else base


def generate_kotlin(classes: list[ClassModel]) -> str:
    """Render Kotlin ``data class`` models."""

    blocks = []
    for cls in classes:
        if not cls.fields:
            blocks.append(f"class {cls.name}")
            continue

        params = [
            f"    val {field_name}: {_kotlin_type(type_ref, nullable)}"
            for field_name, type_ref, nullable in cls.fields
        ]
        body = ",\n".join(params)
        blocks.append(f"data class {cls.name}(\n{body}\n)")
    return "\n\n".join(blocks)


_GENERATORS = {
    "csharp": generate_csharp,
    "java": generate_java,
    "typescript": generate_typescript,
    "python": generate_python,
    "go": generate_go,
    "kotlin": generate_kotlin,
}


def generate_code(payload: JSONValue, language: str, *, root_name: str = "Root") -> str:
    """Infer a model from ``payload`` and render it in ``language``."""

    if language not in _GENERATORS:
        raise ValueError(f"Unsupported code generation language: {language!r}")

    classes, _root_type = infer_classes(payload, root_name=root_name)

    if not classes:
        return "// The root value is a scalar or empty array; nothing to generate."

    return _GENERATORS[language](classes)


def _camel_case(name: str) -> str:
    pascal = _pascal_case(name)
    return pascal[:1].lower() + pascal[1:]
