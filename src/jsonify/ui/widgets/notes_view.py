"""Bookmarks and annotations panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NotesView(QWidget):
    """Lists the document's bookmarked nodes and annotations (by JSON Pointer)."""

    navigate_requested = Signal(str)
    """Emitted with a JSON Pointer when the user asks to jump to a node."""
    bookmark_removed = Signal(str)
    annotation_removed = Signal(str)
    annotation_edit_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        hint = QLabel(
            "Right-click a node in the tree to bookmark it or add a note. "
            "Both are saved with the session."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(QLabel("Bookmarks"))
        self._bookmarks = QListWidget()
        self._bookmarks.itemActivated.connect(self._go_bookmark)
        layout.addWidget(self._bookmarks, 1)

        bookmark_row = QHBoxLayout()
        go_bookmark = QPushButton("Go To")
        go_bookmark.clicked.connect(lambda: self._go_bookmark(self._bookmarks.currentItem()))
        bookmark_row.addWidget(go_bookmark)
        remove_bookmark = QPushButton("Remove")
        remove_bookmark.clicked.connect(self._remove_bookmark)
        bookmark_row.addWidget(remove_bookmark)
        bookmark_row.addStretch(1)
        layout.addLayout(bookmark_row)

        layout.addWidget(QLabel("Annotations"))
        self._annotations = QListWidget()
        self._annotations.itemActivated.connect(self._go_annotation)
        layout.addWidget(self._annotations, 1)

        annotation_row = QHBoxLayout()
        go_annotation = QPushButton("Go To")
        go_annotation.clicked.connect(lambda: self._go_annotation(self._annotations.currentItem()))
        annotation_row.addWidget(go_annotation)
        edit_annotation = QPushButton("Edit Note...")
        edit_annotation.clicked.connect(self._edit_annotation)
        annotation_row.addWidget(edit_annotation)
        remove_annotation = QPushButton("Remove")
        remove_annotation.clicked.connect(self._remove_annotation)
        annotation_row.addWidget(remove_annotation)
        annotation_row.addStretch(1)
        layout.addLayout(annotation_row)

    def set_data(self, bookmarks: list[str], annotations: dict[str, str]) -> None:
        """Refresh both lists."""

        self._bookmarks.clear()
        for pointer in bookmarks:
            item = QListWidgetItem(pointer or "(root)")
            item.setData(Qt.ItemDataRole.UserRole, pointer)
            self._bookmarks.addItem(item)

        self._annotations.clear()
        for pointer, note in annotations.items():
            first_line = note.strip().splitlines()[0] if note.strip() else ""
            item = QListWidgetItem(f"{pointer or '(root)'}  —  {first_line}")
            item.setToolTip(note)
            item.setData(Qt.ItemDataRole.UserRole, pointer)
            self._annotations.addItem(item)

    # -----------------------------------------------------------------

    @staticmethod
    def _pointer_of(item: QListWidgetItem | None) -> str | None:
        return None if item is None else item.data(Qt.ItemDataRole.UserRole)

    def _go_bookmark(self, item: QListWidgetItem | None) -> None:
        pointer = self._pointer_of(item)
        if pointer is not None:
            self.navigate_requested.emit(pointer)

    def _go_annotation(self, item: QListWidgetItem | None) -> None:
        pointer = self._pointer_of(item)
        if pointer is not None:
            self.navigate_requested.emit(pointer)

    def _remove_bookmark(self) -> None:
        pointer = self._pointer_of(self._bookmarks.currentItem())
        if pointer is not None:
            self.bookmark_removed.emit(pointer)

    def _remove_annotation(self) -> None:
        pointer = self._pointer_of(self._annotations.currentItem())
        if pointer is not None:
            self.annotation_removed.emit(pointer)

    def _edit_annotation(self) -> None:
        pointer = self._pointer_of(self._annotations.currentItem())
        if pointer is not None:
            self.annotation_edit_requested.emit(pointer)
