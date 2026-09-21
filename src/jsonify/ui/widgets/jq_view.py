"""jq-lite query user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.jq import JqQueryError, run_jq
from jsonify.core.models import JSONValue
from jsonify.ui.constants import MONOSPACE_FONT


class JqView(QWidget):
    """Widget for running jq-lite queries against the loaded JSON payload."""

    _EXAMPLES = (
        ".",
        ".users[]",
        ".users[] | select(.active == true)",
        ".users[] | .name",
        "keys",
        "length",
        "map(.name)",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._payload: JSONValue | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("jq Query")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        description = QLabel(
            "Run a jq-lite query against the loaded JSON payload. This is a small "
            "pure-Python subset of jq — see the app README for exactly what's supported."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        query_row = QHBoxLayout()
        query_row.addWidget(QLabel("jq:"))

        self._query_combo = QComboBox()
        self._query_combo.setEditable(True)
        self._query_combo.addItems(self._EXAMPLES)
        self._query_combo.setCurrentText(".")
        self._query_combo.setMinimumWidth(400)
        query_row.addWidget(self._query_combo, 1)

        run_button = QPushButton("Run")
        run_button.clicked.connect(self._run_query)
        query_row.addWidget(run_button)

        copy_button = QPushButton("Copy Result")
        copy_button.clicked.connect(self._copy_result)
        query_row.addWidget(copy_button)

        layout.addLayout(query_row)

        self._status_label = QLabel("Load a JSON payload to begin.")
        layout.addWidget(self._status_label)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont(MONOSPACE_FONT))
        layout.addWidget(self._output, 1)

        self._query_combo.lineEdit().returnPressed.connect(self._run_query)

    def set_payload(self, payload: JSONValue) -> None:
        """Set the JSON payload queried by this widget."""

        self._payload = payload
        self._output.clear()
        self._status_label.setText("JSON loaded. Enter a jq query.")

    def clear_payload(self) -> None:
        """Remove the currently loaded JSON payload."""

        self._payload = None
        self._output.clear()
        self._status_label.setText("Load a JSON payload to begin.")

    def _run_query(self) -> None:
        if self._payload is None:
            QMessageBox.warning(
                self, "No JSON Loaded", "Load a JSON payload before running a jq query."
            )
            return

        query = self._query_combo.currentText().strip()
        if not query:
            QMessageBox.warning(self, "jq", "Enter a jq query.")
            return

        try:
            results = run_jq(self._payload, query)
        except JqQueryError as error:
            QMessageBox.critical(self, "Invalid jq Query", str(error))
            return

        self._remember_query(query)
        self._output.setPlainText(json.dumps(results, indent=2, ensure_ascii=False))
        self._status_label.setText(f"{len(results)} result(s).")

    def _remember_query(self, query: str) -> None:
        existing_index = self._query_combo.findText(query)
        if existing_index >= 0:
            self._query_combo.removeItem(existing_index)
        self._query_combo.insertItem(0, query)
        self._query_combo.setCurrentIndex(0)

    def _copy_result(self) -> None:
        text = self._output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
