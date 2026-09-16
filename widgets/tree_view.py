"""
widgets/tree_view.py
---------------------
Builds a QTreeWidget representing the hierarchical structure of a JSON
payload — expand/collapse branches like a classic file explorer /
Notepad++ function list.
"""
from __future__ import annotations

import json
from typing import Any

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem


def create_tree_widget() -> QTreeWidget:
    """Create an empty, styled QTreeWidget with Key/Value columns."""
    tree = QTreeWidget()
    tree.setHeaderLabels(["Key", "Value"])
    tree.setColumnWidth(0, 280)
    tree.setAlternatingRowColors(True)
    return tree


def _type_label(value: Any) -> str:
    if isinstance(value, dict):
        return f"{{{len(value)} keys}}"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return json.dumps(value)


def _add_node(parent_item: QTreeWidgetItem, key: str, value: Any) -> None:
    if isinstance(value, dict):
        node = QTreeWidgetItem([str(key), _type_label(value)])
        parent_item.addChild(node)
        for child_key, child_value in value.items():
            _add_node(node, child_key, child_value)

    elif isinstance(value, list):
        node = QTreeWidgetItem([str(key), _type_label(value)])
        parent_item.addChild(node)
        for index, item in enumerate(value):
            _add_node(node, f"[{index}]", item)

    else:
        node = QTreeWidgetItem([str(key), json.dumps(value)])
        parent_item.addChild(node)


def populate_tree(tree: QTreeWidget, payload: Any) -> None:
    """Clear `tree` and rebuild it from `payload`.

    Args:
        tree: A QTreeWidget previously created by `create_tree_widget()`.
        payload: Any JSON-compatible Python value (parsed payload).
    """
    tree.clear()
    root = QTreeWidgetItem(["root", _type_label(payload)])
    tree.addTopLevelItem(root)

    if isinstance(payload, dict):
        for key, value in payload.items():
            _add_node(root, key, value)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            _add_node(root, f"[{index}]", item)

    tree.expandToDepth(1)
