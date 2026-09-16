"""Tree-view rendering for JSON payloads."""

from __future__ import annotations

import json

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from jsonify.core.models import JSONValue


def create_tree_widget() -> QTreeWidget:
    """
    Create and configure the JSON tree widget.

    Returns:
        Configured QTreeWidget instance.
    """
    tree = QTreeWidget()

    tree.setColumnCount(3)

    tree.setHeaderLabels(
        [
            "Key / Index",
            "Value",
            "Type",
        ]
    )

    tree.setAlternatingRowColors(True)

    tree.setUniformRowHeights(True)

    tree.setColumnWidth(0, 300)
    tree.setColumnWidth(1, 450)
    tree.setColumnWidth(2, 100)

    return tree


def populate_tree(
    tree: QTreeWidget,
    data: JSONValue,
) -> None:
    """
    Populate a tree widget with JSON data.

    Args:
        tree:
            Tree widget to populate.

        data:
            Parsed JSON payload.
    """
    tree.clear()

    tree.setUpdatesEnabled(False)

    try:
        root = QTreeWidgetItem(
            [
                "$",
                _container_summary(data),
                _type_name(data),
            ]
        )

        tree.addTopLevelItem(root)

        _populate_node(
            parent=root,
            value=data,
        )

        root.setExpanded(True)

    finally:
        tree.setUpdatesEnabled(True)


def _populate_node(
    parent: QTreeWidgetItem,
    value: JSONValue,
) -> None:
    """Recursively add JSON children to a tree item."""

    if isinstance(value, dict):
        for key, child_value in value.items():
            item = QTreeWidgetItem(
                [
                    str(key),
                    _display_value(child_value),
                    _type_name(child_value),
                ]
            )

            parent.addChild(item)

            if _is_container(child_value):
                _populate_node(
                    item,
                    child_value,
                )

    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            item = QTreeWidgetItem(
                [
                    f"[{index}]",
                    _display_value(child_value),
                    _type_name(child_value),
                ]
            )

            parent.addChild(item)

            if _is_container(child_value):
                _populate_node(
                    item,
                    child_value,
                )


def _is_container(
    value: JSONValue,
) -> bool:
    """Return whether a JSON value contains child values."""

    return isinstance(
        value,
        (dict, list),
    )


def _container_summary(
    value: JSONValue,
) -> str:
    """Return a short description for containers."""

    if isinstance(value, dict):
        count = len(value)

        return (
            f"{count} key"
            if count == 1
            else f"{count} keys"
        )

    if isinstance(value, list):
        count = len(value)

        return (
            f"{count} item"
            if count == 1
            else f"{count} items"
        )

    return _display_value(value)


def _display_value(
    value: JSONValue,
) -> str:
    """Convert a JSON value into display text."""

    if isinstance(value, dict):
        return _container_summary(value)

    if isinstance(value, list):
        return _container_summary(value)

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, str):
        return value

    return str(value)


def _type_name(
    value: JSONValue,
) -> str:
    """Return a JSON-friendly type name."""

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