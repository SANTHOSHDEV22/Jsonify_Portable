"""A VS Code-style command palette (Ctrl+Shift+P).

Lists every registered ``QAction`` in the application and lets the user
fuzzy-filter and trigger one by name instead of hunting through menus.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class CommandPalette(QDialog):
    """A searchable list of every available action, triggerable by name."""

    def __init__(self, actions: list[QAction], parent=None) -> None:
        super().__init__(parent)

        self.setObjectName("commandPalette")
        self.setWindowTitle("Command Palette")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setMinimumWidth(560)

        self._actions = [action for action in actions if action.text().strip()]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Type a command name...")
        self._search_box.textChanged.connect(self._refresh_results)
        layout.addWidget(self._search_box)

        self._results_list = QListWidget()
        self._results_list.itemActivated.connect(self._activate_item)
        layout.addWidget(self._results_list)

        self._search_box.installEventFilter(self)

        self._refresh_results("")
        self._search_box.setFocus()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (Qt override)
        if watched is self._search_box and event.type() == event.Type.KeyPress:
            key = event.key()

            if key == Qt.Key.Key_Down:
                self._move_selection(1)
                return True

            if key == Qt.Key.Key_Up:
                self._move_selection(-1)
                return True

            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self._results_list.currentItem()
                if item is not None:
                    self._activate_item(item)
                return True

            if key == Qt.Key.Key_Escape:
                self.reject()
                return True

        return super().eventFilter(watched, event)

    def _move_selection(self, delta: int) -> None:
        count = self._results_list.count()
        if count == 0:
            return

        row = self._results_list.currentRow()
        row = max(0, min(count - 1, row + delta))
        self._results_list.setCurrentRow(row)

    def _refresh_results(self, query: str) -> None:
        self._results_list.clear()
        needle = query.strip().lower()

        for action in self._actions:
            title = action.text().replace("&", "")

            if needle and needle not in title.lower():
                continue

            shortcut = action.shortcut().toString()
            label = f"{title}    {shortcut}" if shortcut else title

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, action)
            self._results_list.addItem(item)

        if self._results_list.count() > 0:
            self._results_list.setCurrentRow(0)

    def _activate_item(self, item: QListWidgetItem) -> None:
        action = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        if isinstance(action, QAction) and action.isEnabled():
            action.trigger()
