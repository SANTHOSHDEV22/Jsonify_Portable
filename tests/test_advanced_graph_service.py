"""Tests for AdvancedGraphService."""

from __future__ import annotations

from jsonify.services.advanced_graph_service import (
    AdvancedGraphService,
)


def test_simple_object() -> None:
    service = AdvancedGraphService()

    result = service.build(
        {
            "id": 1,
            "name": "Alice",
        }
    )

    assert result.statistics.total_nodes == 3

    assert result.statistics.object_nodes == 1

    assert result.statistics.primitive_nodes == 2


def test_root_node() -> None:
    service = AdvancedGraphService()

    result = service.build(
        {
            "id": 1,
        }
    )

    root = result.nodes[0]

    assert root.node_id == 0
    assert root.parent_id is None
    assert root.path == "$"
    assert root.node_type == "object"


def test_nested_paths() -> None:
    service = AdvancedGraphService()

    result = service.build(
        {
            "user": {
                "name": "Alice",
            }
        }
    )

    paths = {node.path for node in result.nodes}

    assert "$" in paths
    assert "$.user" in paths
    assert "$.user.name" in paths


def test_array_paths() -> None:
    service = AdvancedGraphService()

    result = service.build(
        {
            "users": [
                {
                    "id": 1,
                }
            ]
        }
    )

    paths = {node.path for node in result.nodes}

    assert "$.users" in paths
    assert "$.users[0]" in paths
    assert "$.users[0].id" in paths


def test_json_types() -> None:
    service = AdvancedGraphService()

    result = service.build(
        {
            "string": "hello",
            "integer": 10,
            "number": 10.5,
            "boolean": True,
            "nothing": None,
            "array": [],
            "object": {},
        }
    )

    types = {node.name: node.node_type for node in result.nodes}

    assert types["string"] == "string"
    assert types["integer"] == "integer"
    assert types["number"] == "number"
    assert types["boolean"] == "boolean"
    assert types["nothing"] == "null"
    assert types["array"] == "array"
    assert types["object"] == "object"


def test_graph_limit() -> None:
    service = AdvancedGraphService(node_limit=10)

    payload = list(range(100))

    result = service.build(payload)

    assert len(result.nodes) == 10
    assert result.truncated is True


def test_graph_not_truncated() -> None:
    service = AdvancedGraphService(node_limit=100)

    result = service.build(
        {
            "id": 1,
            "name": "Alice",
        }
    )

    assert result.truncated is False


def test_max_depth() -> None:
    service = AdvancedGraphService()

    result = service.build(
        {
            "a": {
                "b": {
                    "c": 1,
                }
            }
        }
    )

    assert result.statistics.max_depth == 3


def test_special_key_path() -> None:
    service = AdvancedGraphService()

    result = service.build(
        {
            "first name": "Alice",
        }
    )

    paths = {node.path for node in result.nodes}

    assert '$["first name"]' in paths


def test_long_value_preview() -> None:
    service = AdvancedGraphService(preview_length=5)

    result = service.build(
        {
            "value": "abcdefghij",
        }
    )

    value_node = next(node for node in result.nodes if node.name == "value")

    assert value_node.value == "abcde..."
