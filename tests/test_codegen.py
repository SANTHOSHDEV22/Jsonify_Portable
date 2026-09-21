"""Tests for the code-generation model inference and language renderers."""

from __future__ import annotations

from jsonify.core.codegen import generate_code, infer_classes

_SAMPLE = {
    "id": 1,
    "name": "Alice",
    "active": True,
    "score": 4.5,
    "nickname": None,
    "address": {"city": "Springfield"},
    "tags": ["a", "b"],
}


def test_infer_classes_root_object() -> None:
    classes, root_type = infer_classes(_SAMPLE, root_name="User")

    assert root_type.kind == "object"
    assert root_type.class_name == "User"

    names = {cls.name for cls in classes}
    assert "User" in names
    assert "Address" in names


def test_infer_classes_nullable_field_marked() -> None:
    classes, _root = infer_classes(_SAMPLE, root_name="User")
    user = next(cls for cls in classes if cls.name == "User")

    nickname_field = next(f for f in user.fields if f[0] == "nickname")
    assert nickname_field[2] is True  # nullable flag


def test_infer_classes_array_of_objects_merges_shape() -> None:
    payload = {"users": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}

    classes, _root = infer_classes(payload, root_name="Root")
    names = {cls.name for cls in classes}

    assert "User" in names or "Users" in names  # singularization isn't attempted; just present


def test_generate_csharp_contains_class_and_properties() -> None:
    code = generate_code(_SAMPLE, "csharp", root_name="User")

    assert "public class User" in code
    assert "public int Id { get; set; }" in code
    assert "public string Name { get; set; }" in code
    assert "public bool Active { get; set; }" in code
    assert "public Address Address { get; set; }" in code


def test_generate_typescript_contains_interface() -> None:
    code = generate_code(_SAMPLE, "typescript", root_name="User")

    assert "export interface User {" in code
    assert "id: number;" in code
    assert "nickname?: null;" in code


def test_generate_python_contains_dataclass() -> None:
    code = generate_code(_SAMPLE, "python", root_name="User")

    assert "@dataclass" in code
    assert "class User:" in code
    assert "id: int" in code


def test_generate_java_contains_pojo() -> None:
    code = generate_code(_SAMPLE, "java", root_name="User")

    assert "public class User {" in code
    assert "private int id;" in code
    assert "public int getId()" in code


def test_generate_go_contains_struct_with_json_tags() -> None:
    code = generate_code(_SAMPLE, "go", root_name="User")

    assert "type User struct {" in code
    assert '`json:"id"`' in code


def test_generate_kotlin_contains_data_class() -> None:
    code = generate_code(_SAMPLE, "kotlin", root_name="User")

    assert "data class User(" in code
    assert "val id: Int" in code


def test_generate_code_array_of_primitives_has_no_classes() -> None:
    code = generate_code([1, 2, 3], "python", root_name="Root")

    assert "nothing to generate" in code


def test_generate_code_unsupported_language_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        generate_code({"a": 1}, "cobol")
