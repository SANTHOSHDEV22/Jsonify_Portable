"""Lazy-loading tree view for large JSON payloads."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    Signal,
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHeaderView,
    QMenu,
    QTreeView,
)

from jsonify.core.formatter import minify as minify_json
from jsonify.core.models import JSONValue
from jsonify.core.pointer import PathSegment, to_json_path, to_json_pointer
from jsonify.services.large_json_service import (
    LargeJsonService,
)

# Shared default for Qt model overrides (an invalid index means "the root").
_INVALID_INDEX = QModelIndex()


class JsonTreeNode:
    """Represents one lazily loaded JSON tree node."""

    def __init__(
        self,
        *,
        key: str,
        value: JSONValue,
        parent: JsonTreeNode | None = None,
        segment: PathSegment | None = None,
    ) -> None:
        self.key = key
        self.value = value
        self.parent = parent
        self.segment = segment

        self.children: list[JsonTreeNode] = []

        self.children_loaded = False

    def path_segments(self) -> list[PathSegment]:
        """Return this node's full path from the root, as raw segments."""

        segments: list[PathSegment] = []
        node: JsonTreeNode | None = self

        while node is not None and node.segment is not None:
            segments.append(node.segment)
            node = node.parent

        segments.reverse()
        return segments

    @property
    def has_children(self) -> bool:
        """Return whether this value can contain children."""

        return (isinstance(self.value, dict) and bool(self.value)) or (
            isinstance(self.value, list) and bool(self.value)
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
                        segment=str(key),
                    )
                )

        elif isinstance(self.value, list):
            for index, value in enumerate(self.value):
                self.children.append(
                    JsonTreeNode(
                        key=f"[{index}]",
                        value=value,
                        parent=self,
                        segment=index,
                    )
                )

        self.children_loaded = True

    def row(self) -> int:
        """Return this node's row inside its parent."""

        if self.parent is None:
            return 0

        try:
            return self.parent.children.index(self)
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

        self._service = service if service is not None else LargeJsonService()

        self._root = JsonTreeNode(
            key="$",
            value=payload,
        )

        # Only the root's immediate children are created initially.
        self._root.load_children()

    def columnCount(
        self,
        parent: QModelIndex = _INVALID_INDEX,
    ) -> int:
        """Return number of columns."""

        return len(self.HEADERS)

    def rowCount(
        self,
        parent: QModelIndex = _INVALID_INDEX,
    ) -> int:
        """Return number of currently available child rows."""

        if parent.isValid():
            node = self._node_from_index(parent)
        else:
            node = self._root

        if not node.children_loaded:
            return 0

        return node.child_count()

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex = _INVALID_INDEX,
    ) -> QModelIndex:
        """Create an index for a child node."""

        if row < 0 or column < 0:
            return QModelIndex()

        if parent.isValid():
            parent_node = self._node_from_index(parent)
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

        node = self._node_from_index(index)

        parent_node = node.parent

        if parent_node is None or parent_node is self._root:
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

        node = self._node_from_index(index)

        column = index.column()

        if column == 0:
            return node.key

        if column == 1:
            return self._service.preview(node.value)

        if column == 2:
            return self._type_name(node.value)

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return column headers."""

        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]

        return None

    def hasChildren(
        self,
        parent: QModelIndex = _INVALID_INDEX,
    ) -> bool:
        """Tell Qt whether a node can be expanded."""

        if not parent.isValid():
            return bool(self._root.children)

        node = self._node_from_index(parent)

        return node.has_children

    def canFetchMore(
        self,
        parent: QModelIndex,
    ) -> bool:
        """Return whether children still need to be loaded."""

        if not parent.isValid():
            return False

        node = self._node_from_index(parent)

        return node.has_children and not node.children_loaded

    def fetchMore(
        self,
        parent: QModelIndex,
    ) -> None:
        """Load direct children when the node is expanded."""

        if not parent.isValid():
            return

        node = self._node_from_index(parent)

        if node.children_loaded or not node.has_children:
            return

        count = self._raw_child_count(node.value)

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
            raise RuntimeError("Invalid JSON tree model index.")

        return node

    def node_at(self, index: QModelIndex) -> JsonTreeNode | None:
        """Public accessor: return the node at ``index``, or ``None``."""

        if not index.isValid():
            return None

        return self._node_from_index(index)

    def index_for_node(self, node: JsonTreeNode) -> QModelIndex:
        """Return the model index for a given node."""

        if node is self._root:
            return QModelIndex()

        return self.createIndex(node.row(), 0, node)

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

    type_name = _type_name


class LazyJsonTreeView(QTreeView):
    """Tree widget optimized for large JSON documents."""

    node_selected = Signal(object)
    bookmark_requested = Signal(object)
    """Emitted with a node's path segments when "Bookmark" is chosen."""
    annotate_requested = Signal(object)
    """Emitted with a node's path segments when "Add / Edit Note" is chosen."""
    """Emitted with the selected ``JsonTreeNode`` (or ``None``)."""

    def __init__(
        self,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)

        self._json_model: LazyJsonTreeModel | None = None

        self.setAlternatingRowColors(True)

        self.setUniformRowHeights(True)

        self.setAnimated(False)

        self.setSortingEnabled(False)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        header = self.header()

        header.setStretchLastSection(False)

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Interactive,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Interactive,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Interactive,
        )

        # Column widths are applied in set_payload() instead of here:
        # the header has no real columns until a model with data exists,
        # so setColumnWidth() calls made before setModel() are silently
        # discarded and every column falls back to Qt's 100px default.
        self._columns_initialized = False

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Display a JSON payload."""

        self._json_model = LazyJsonTreeModel(payload)

        self.setModel(self._json_model)

        if self.selectionModel() is not None:
            self.selectionModel().currentChanged.connect(self._on_current_changed)

        self.collapseAll()

        if not self._columns_initialized:
            self.setColumnWidth(
                0,
                220,
            )

            self.setColumnWidth(
                1,
                360,
            )

            self.setColumnWidth(
                2,
                100,
            )

            self._columns_initialized = True

    def clear_payload(self) -> None:
        """Clear the JSON tree."""

        self._json_model = None

        self.setModel(None)

    def select_path(self, segments: list[PathSegment]) -> bool:
        """Expand and select the node at ``segments`` (e.g. for search).

        Returns ``False`` if the path doesn't resolve against the current
        payload (nothing changes in that case).
        """

        if self._json_model is None:
            return False

        model = self._json_model
        node = model._root
        parent_index = QModelIndex()

        for segment in segments:
            if model.canFetchMore(parent_index):
                model.fetchMore(parent_index)

            match = next(
                (
                    child
                    for child in node.children
                    if child.segment == segment or str(child.segment) == str(segment)
                ),
                None,
            )
            if match is None:
                return False

            child_index = model.index_for_node(match)

            # Expand the ancestor (not the node itself) so this row becomes
            # visible; the invisible root (an invalid index) can't be
            # expanded, but top-level rows are shown without it anyway.
            if parent_index.isValid():
                self.expand(parent_index)

            parent_index = child_index
            node = match

        self.setCurrentIndex(parent_index)
        self.scrollTo(parent_index)
        return True

    # -----------------------------------------------------------------
    # Selection / type inspector
    # -----------------------------------------------------------------

    def _on_current_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if self._json_model is None:
            self.node_selected.emit(None)
            return

        self.node_selected.emit(self._json_model.node_at(current))

    # -----------------------------------------------------------------
    # Context menu: copy tools + jump to parent/root
    # -----------------------------------------------------------------

    def _show_context_menu(self, position) -> None:
        index = self.indexAt(position)
        if not index.isValid() or self._json_model is None:
            return

        node = self._json_model.node_at(index)
        if node is None:
            return

        menu = QMenu(self)

        copy_key_action = QAction("Copy Key", self)
        copy_key_action.triggered.connect(lambda: self._copy_to_clipboard(node.key))
        menu.addAction(copy_key_action)

        copy_value_action = QAction("Copy Value", self)
        copy_value_action.triggered.connect(
            lambda: self._copy_to_clipboard(self._value_as_text(node.value))
        )
        menu.addAction(copy_value_action)

        copy_node_action = QAction("Copy Node (JSON)", self)
        copy_node_action.triggered.connect(lambda: self._copy_to_clipboard(minify_json(node.value)))
        menu.addAction(copy_node_action)

        menu.addSeparator()

        segments = node.path_segments()

        copy_path_action = QAction("Copy JSONPath", self)
        copy_path_action.triggered.connect(lambda: self._copy_to_clipboard(to_json_path(segments)))
        menu.addAction(copy_path_action)

        copy_pointer_action = QAction("Copy JSON Pointer", self)
        copy_pointer_action.triggered.connect(
            lambda: self._copy_to_clipboard(to_json_pointer(segments))
        )
        menu.addAction(copy_pointer_action)

        menu.addSeparator()

        if node.parent is not None and node.parent.segment is not None:
            jump_parent_action = QAction("Jump to Parent", self)
            jump_parent_action.triggered.connect(lambda: self._select_node(node.parent))
            menu.addAction(jump_parent_action)

        menu.addSeparator()

        bookmark_action = QAction("Bookmark Node", self)
        bookmark_action.triggered.connect(lambda: self.bookmark_requested.emit(segments))
        menu.addAction(bookmark_action)

        note_action = QAction("Add / Edit Note...", self)
        note_action.triggered.connect(lambda: self.annotate_requested.emit(segments))
        menu.addAction(note_action)

        menu.addSeparator()

        jump_root_action = QAction("Jump to Root", self)
        jump_root_action.triggered.connect(self._select_root)
        menu.addAction(jump_root_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def _select_node(self, node: JsonTreeNode | None) -> None:
        if node is None or self._json_model is None:
            return

        index = self._json_model.index_for_node(node)
        self.setCurrentIndex(index)
        self.scrollTo(index)

    def _select_root(self) -> None:
        if self.model() is None or self.model().rowCount() == 0:
            return

        self.setCurrentIndex(self.model().index(0, 0))
        self.collapseAll()

    @staticmethod
    def _copy_to_clipboard(text: str) -> None:
        QApplication.clipboard().setText(text)

    @staticmethod
    def _value_as_text(value: JSONValue) -> str:
        if isinstance(value, dict | list):
            return minify_json(value)
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
