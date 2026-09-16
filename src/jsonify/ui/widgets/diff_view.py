"""JSON Diff user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.diff import DiffType, JsonDiff
from jsonify.core.models import JSONValue
from jsonify.services.diff_service import DiffService
from jsonify.ui.constants import MONOSPACE_FONT


class DiffView(QWidget):
    """Widget used to compare two JSON documents."""

    def __init__(
        self,
        diff_service: DiffService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._diff_service = (
            diff_service
            if diff_service is not None
            else DiffService()
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the JSON Diff interface."""

        layout = QVBoxLayout(self)

        title = QLabel("JSON Diff")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)

        layout.addWidget(title)

        description = QLabel(
            "Compare two JSON documents and inspect added, "
            "removed, changed, and type-changed values."
        )
        description.setWordWrap(True)

        layout.addWidget(description)

        editor_splitter = QSplitter(Qt.Orientation.Horizontal)

        old_panel = self._create_editor_panel(
            title="Original JSON",
            is_old=True,
        )

        new_panel = self._create_editor_panel(
            title="New JSON",
            is_old=False,
        )

        editor_splitter.addWidget(old_panel)
        editor_splitter.addWidget(new_panel)

        editor_splitter.setStretchFactor(0, 1)
        editor_splitter.setStretchFactor(1, 1)

        layout.addWidget(editor_splitter, 1)

        controls = QHBoxLayout()

        self._compare_button = QPushButton("Compare")
        self._compare_button.clicked.connect(
            self._compare
        )

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(
            self._clear
        )

        self._summary_label = QLabel(
            "No comparison performed."
        )

        controls.addWidget(self._compare_button)
        controls.addWidget(clear_button)
        controls.addSpacing(15)
        controls.addWidget(self._summary_label)
        controls.addStretch()

        layout.addLayout(controls)

        results_label = QLabel("Differences")

        results_font = results_label.font()
        results_font.setBold(True)

        results_label.setFont(results_font)

        layout.addWidget(results_label)

        self._results_table = QTableWidget()

        self._results_table.setColumnCount(4)

        self._results_table.setHorizontalHeaderLabels(
            [
                "Change",
                "Path",
                "Old Value",
                "New Value",
            ]
        )

        self._results_table.setAlternatingRowColors(True)
        self._results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._results_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        header = self._results_table.horizontalHeader()

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
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )

        layout.addWidget(self._results_table, 1)

    def _create_editor_panel(
        self,
        title: str,
        is_old: bool,
    ) -> QWidget:
        """Create one side of the JSON comparison editor."""

        panel = QWidget()

        layout = QVBoxLayout(panel)

        label = QLabel(title)

        label_font = label.font()
        label_font.setBold(True)

        label.setFont(label_font)

        editor = QPlainTextEdit()

        editor.setPlaceholderText(
            f"Paste {title.lower()} here..."
        )

        editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        font = QFont(MONOSPACE_FONT)
        editor.setFont(font)

        layout.addWidget(label)
        layout.addWidget(editor)

        if is_old:
            self._old_editor = editor
        else:
            self._new_editor = editor

        return panel

    def _compare(self) -> None:
        """Compare JSON entered in both editors."""

        old_text = self._old_editor.toPlainText().strip()
        new_text = self._new_editor.toPlainText().strip()

        if not old_text or not new_text:
            QMessageBox.warning(
                self,
                "JSON Diff",
                "Paste both the original JSON and new JSON "
                "before comparing.",
            )
            return

        try:
            differences = self._diff_service.compare_text(
                old_text=old_text,
                new_text=new_text,
            )
        except json.JSONDecodeError as error:
            QMessageBox.critical(
                self,
                "Invalid JSON",
                self._format_json_error(error),
            )
            return

        self._display_differences(differences)

    def _display_differences(
        self,
        differences: list[JsonDiff],
    ) -> None:
        """Display comparison results."""

        self._results_table.setRowCount(0)

        if not differences:
            self._summary_label.setText(
                "JSON documents are identical."
            )
            return

        counts = {
            DiffType.ADDED: 0,
            DiffType.REMOVED: 0,
            DiffType.CHANGED: 0,
            DiffType.TYPE_CHANGED: 0,
        }

        self._results_table.setRowCount(
            len(differences)
        )

        for row, difference in enumerate(differences):
            counts[difference.diff_type] += 1

            change_item = QTableWidgetItem(
                self._change_label(difference)
            )

            path_item = QTableWidgetItem(
                difference.path
            )

            old_item = QTableWidgetItem(
                self._display_value(
                    difference.old_value,
                    missing=(
                        difference.diff_type
                        == DiffType.ADDED
                    ),
                )
            )

            new_item = QTableWidgetItem(
                self._display_value(
                    difference.new_value,
                    missing=(
                        difference.diff_type
                        == DiffType.REMOVED
                    ),
                )
            )

            color = self._change_color(
                difference.diff_type
            )

            change_item.setForeground(color)

            change_font = change_item.font()
            change_font.setBold(True)
            change_item.setFont(change_font)

            self._results_table.setItem(
                row,
                0,
                change_item,
            )

            self._results_table.setItem(
                row,
                1,
                path_item,
            )

            self._results_table.setItem(
                row,
                2,
                old_item,
            )

            self._results_table.setItem(
                row,
                3,
                new_item,
            )

        self._summary_label.setText(
            (
                f"{len(differences)} difference(s) — "
                f"{counts[DiffType.ADDED]} added, "
                f"{counts[DiffType.REMOVED]} removed, "
                f"{counts[DiffType.CHANGED]} changed, "
                f"{counts[DiffType.TYPE_CHANGED]} type changed"
            )
        )

    def _clear(self) -> None:
        """Clear both editors and comparison results."""

        self._old_editor.clear()
        self._new_editor.clear()

        self._results_table.setRowCount(0)

        self._summary_label.setText(
            "No comparison performed."
        )

    @staticmethod
    def _change_label(
        difference: JsonDiff,
    ) -> str:
        """Return display label for a difference."""

        labels = {
            DiffType.ADDED: "Added",
            DiffType.REMOVED: "Removed",
            DiffType.CHANGED: "Changed",
            DiffType.TYPE_CHANGED: "Type Changed",
        }

        return (
            f"{difference.symbol} "
            f"{labels[difference.diff_type]}"
        )

    @staticmethod
    def _change_color(
        diff_type: DiffType,
    ) -> QColor:
        """Return display color for a difference."""

        colors = {
            DiffType.ADDED: QColor("#4EC9B0"),
            DiffType.REMOVED: QColor("#F44747"),
            DiffType.CHANGED: QColor("#DCDCAA"),
            DiffType.TYPE_CHANGED: QColor("#CE9178"),
        }

        return colors[diff_type]

    @staticmethod
    def _display_value(
        value: JSONValue,
        *,
        missing: bool,
    ) -> str:
        """Convert a JSON value to readable text."""

        if missing:
            return "—"

        if value is None:
            return "null"

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, str):
            return value

        if isinstance(value, (dict, list)):
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return str(value)

    @staticmethod
    def _format_json_error(
        error: json.JSONDecodeError,
    ) -> str:
        """Create a readable JSON parsing error."""

        return (
            f"{error.msg}\n\n"
            f"Line: {error.lineno}\n"
            f"Column: {error.colno}"
        )