"""Lazy-loading tree view for large JSON payloads."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
)
from PySide6.QtWidgets import (
    QHeaderView,
    QTreeView,
)

from jsonify.core.models import JSONValue
from jsonify.services.large_json_service import (
    LargeJsonService,
)


class JsonTreeNode:
    """Represents one lazily loaded JSON tree node."""

    def __init__(
        self,
        *,
        key: str,
        value: JSONValue,
        parent: JsonTreeNode | None = None,
    ) -> None:
        self.key = key
        self.value = value
        self.parent = parent

        self.children: list[JsonTreeNode] = []

        self.children_loaded = False

    @property
    def has_children(self) -> bool:
        """Return whether this value can contain children."""

        return (
            isinstance(self.value, dict)
            and bool(self.value)
        ) or (
            isinstance(self.value, list)
            and bool(self.value)
        )

    def child_count(self) -> int:
        """Return the number of loaded children."""

        return len(self.children)

    def load_children(self) -> None:
        """Materialize direct children only."""

        if self.children_loaded:
            return

        if isinstance(self.value, dict):
            for key, value in self.value.items():
                self.children.append(
                    JsonTreeNode(
                        key=str(key),
                        value=value,
                        parent=self,
                    )
                )

        elif isinstance(self.value, list):
            for index, value in enumerate(
                self.value
            ):
                self.children.append(
                    JsonTreeNode(
                        key=f"[{index}]",
                        value=value,
                        parent=self,
                    )
                )

        self.children_loaded = True

    def row(self) -> int:
        """Return this node's row inside its parent."""

        if self.parent is None:
            return 0

        try:
            return self.parent.children.index(
                self
            )
        except ValueError:
            return 0


class LazyJsonTreeModel(QAbstractItemModel):
    """Qt model that materializes JSON nodes on demand."""

    HEADERS = (
        "Key",
        "Value",
        "Type",
    )

    def __init__(
        self,
        payload: JSONValue,
        *,
        service: LargeJsonService | None = None,
    ) -> None:
        super().__init__()

        self._service = (
            service
            if service is not None
            else LargeJsonService()
        )

        self._root = JsonTreeNode(
            key="$",
            value=payload,
        )

        # Only the root's immediate children are created initially.
        self._root.load_children()

    def columnCount(
        self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        """Return number of columns."""

        return len(self.HEADERS)

    def rowCount(
        self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        """Return number of currently available child rows."""

        if parent.isValid():
            node = self._node_from_index(
                parent
            )
        else:
            node = self._root

        if not node.children_loaded:
            return 0

        return node.child_count()

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex = QModelIndex(),
    ) -> QModelIndex:
        """Create an index for a child node."""

        if row < 0 or column < 0:
            return QModelIndex()

        if parent.isValid():
            parent_node = self._node_from_index(
                parent
            )
        else:
            parent_node = self._root

        if not parent_node.children_loaded:
            return QModelIndex()

        if row >= parent_node.child_count():
            return QModelIndex()

        child = parent_node.children[row]

        return self.createIndex(
            row,
            column,
            child,
        )

    def parent(
        self,
        index: QModelIndex,
    ) -> QModelIndex:
        """Return a node's parent index."""

        if not index.isValid():
            return QModelIndex()

        node = self._node_from_index(
            index
        )

        parent_node = node.parent

        if (
            parent_node is None
            or parent_node is self._root
        ):
            return QModelIndex()

        return self.createIndex(
            parent_node.row(),
            0,
            parent_node,
        )

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return data displayed by Qt."""

        if not index.isValid():
            return None

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        node = self._node_from_index(
            index
        )

        column = index.column()

        if column == 0:
            return node.key

        if column == 1:
            return self._service.preview(
                node.value
            )

        if column == 2:
            return self._type_name(
                node.value
            )

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return column headers."""

        if (
            orientation
            == Qt.Orientation.Horizontal
            and role
            == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]

        return None

    def hasChildren(
        self,
        parent: QModelIndex = QModelIndex(),
    ) -> bool:
        """Tell Qt whether a node can be expanded."""

        if not parent.isValid():
            return bool(
                self._root.children
            )

        node = self._node_from_index(
            parent
        )

        return node.has_children

    def canFetchMore(
        self,
        parent: QModelIndex,
    ) -> bool:
        """Return whether children still need to be loaded."""

        if not parent.isValid():
            return False

        node = self._node_from_index(
            parent
        )

        return (
            node.has_children
            and not node.children_loaded
        )

    def fetchMore(
        self,
        parent: QModelIndex,
    ) -> None:
        """Load direct children when the node is expanded."""

        if not parent.isValid():
            return

        node = self._node_from_index(
            parent
        )

        if (
            node.children_loaded
            or not node.has_children
        ):
            return

        count = self._raw_child_count(
            node.value
        )

        if count <= 0:
            node.children_loaded = True
            return

        self.beginInsertRows(
            parent,
            0,
            count - 1,
        )

        node.load_children()

        self.endInsertRows()

    @staticmethod
    def _raw_child_count(
        value: JSONValue,
    ) -> int:
        """Return direct child count without creating nodes."""

        if isinstance(value, dict):
            return len(value)

        if isinstance(value, list):
            return len(value)

        return 0

    @staticmethod
    def _node_from_index(
        index: QModelIndex,
    ) -> JsonTreeNode:
        """Return the node represented by an index."""

        node = index.internalPointer()

        if not isinstance(
            node,
            JsonTreeNode,
        ):
            raise RuntimeError(
                "Invalid JSON tree model index."
            )

        return node

    @staticmethod
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


class LazyJsonTreeView(QTreeView):
    """Tree widget optimized for large JSON documents."""

    def __init__(
        self,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)

        self._json_model: (
            LazyJsonTreeModel | None
        ) = None

        self.setAlternatingRowColors(
            True
        )

        self.setUniformRowHeights(
            True
        )

        self.setAnimated(
            False
        )

        self.setSortingEnabled(
            False
        )

        header = self.header()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Display a JSON payload."""

        self._json_model = (
            LazyJsonTreeModel(
                payload
            )
        )

        self.setModel(
            self._json_model
        )

        self.collapseAll()

    def clear_payload(self) -> None:
        """Clear the JSON tree."""

        self._json_model = None

        self.setModel(None)