"""Export user-interface widget for Jsonify."""

from __future__ import annotations

import json

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.models import JSONValue
from jsonify.services.export_service import (
    ExportError,
    ExportService,
)
from jsonify.ui.constants import MONOSPACE_FONT


class ExportView(QWidget):
    """Widget for exporting JSON and graph output."""

    graph_export_requested = Signal(str)

    def __init__(
        self,
        export_service: ExportService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._export_service = (
            export_service
            if export_service is not None
            else ExportService()
        )

        self._payload: JSONValue | None = None
        self._masked_payload: JSONValue | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the export interface."""

        layout = QVBoxLayout(self)

        title = QLabel("Export")

        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)

        title.setFont(title_font)

        layout.addWidget(title)

        description = QLabel(
            "Export JSON data or the current graph "
            "to a file."
        )

        description.setWordWrap(True)

        layout.addWidget(description)

        options = QHBoxLayout()

        options.addWidget(
            QLabel("Export:")
        )

        self._export_type = QComboBox()

        self._export_type.addItem(
            "Formatted JSON",
            "json",
        )

        self._export_type.addItem(
            "Masked JSON",
            "masked_json",
        )

        self._export_type.addItem(
            "Graph SVG",
            "svg",
        )

        self._export_type.addItem(
            "Graph PNG",
            "png",
        )

        self._export_type.addItem(
            "Graph PDF",
            "pdf",
        )

        options.addWidget(
            self._export_type
        )

        self._export_button = QPushButton(
            "Export..."
        )

        self._export_button.clicked.connect(
            self._export
        )

        options.addWidget(
            self._export_button
        )

        options.addStretch()

        layout.addLayout(options)

        preview_label = QLabel(
            "JSON Preview"
        )

        preview_font = preview_label.font()
        preview_font.setBold(True)

        preview_label.setFont(
            preview_font
        )

        layout.addWidget(
            preview_label
        )

        self._preview = QPlainTextEdit()

        self._preview.setReadOnly(True)

        self._preview.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        self._preview.setFont(
            QFont(MONOSPACE_FONT)
        )

        layout.addWidget(
            self._preview,
            1,
        )

        self._status_label = QLabel(
            "Load JSON to begin."
        )

        layout.addWidget(
            self._status_label
        )

        self._export_type.currentIndexChanged.connect(
            self._refresh_preview
        )

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Set the currently loaded JSON payload."""

        self._payload = payload

        self._refresh_preview()

        self._status_label.setText(
            "JSON loaded. Choose an export format."
        )

    def set_masked_payload(
        self,
        payload: JSONValue | None,
    ) -> None:
        """Set the latest masked JSON payload."""

        self._masked_payload = payload

        self._refresh_preview()

    def clear_payload(self) -> None:
        """Clear export data."""

        self._payload = None
        self._masked_payload = None

        self._preview.clear()

        self._status_label.setText(
            "Load JSON to begin."
        )

    def _refresh_preview(self) -> None:
        """Refresh the JSON preview."""

        export_type = (
            self._export_type.currentData()
        )

        if export_type == "masked_json":
            payload = self._masked_payload
        else:
            payload = self._payload

        if payload is None:
            self._preview.clear()
            return

        self._preview.setPlainText(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
        )

    def _export(self) -> None:
        """Export the selected content."""

        export_type = (
            self._export_type.currentData()
        )

        if export_type == "json":
            self._export_json()
            return

        if export_type == "masked_json":
            self._export_masked_json()
            return

        if export_type in {
            "svg",
            "png",
            "pdf",
        }:
            self._export_graph(
                export_type
            )

    def _export_json(self) -> None:
        """Export the loaded JSON."""

        if self._payload is None:
            QMessageBox.warning(
                self,
                "Export",
                "Load JSON before exporting.",
            )
            return

        file_name, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Export JSON",
                "jsonify-export.json",
                "JSON Files (*.json)",
            )
        )

        if not file_name:
            return

        try:
            path = (
                self._export_service.export_json(
                    self._payload,
                    file_name,
                )
            )

        except ExportError as error:
            self._show_error(error)
            return

        self._status_label.setText(
            f"Exported: {path}"
        )

    def _export_masked_json(self) -> None:
        """Export the latest masked JSON."""

        if self._masked_payload is None:
            QMessageBox.warning(
                self,
                "Export",
                (
                    "Create a masked JSON result "
                    "before exporting it."
                ),
            )
            return

        file_name, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Export Masked JSON",
                "jsonify-masked.json",
                "JSON Files (*.json)",
            )
        )

        if not file_name:
            return

        try:
            path = (
                self._export_service.export_json(
                    self._masked_payload,
                    file_name,
                )
            )

        except ExportError as error:
            self._show_error(error)
            return

        self._status_label.setText(
            f"Exported masked JSON: {path}"
        )

    def _export_graph(
        self,
        export_type: str,
    ) -> None:
        """Request graph export from MainWindow."""

        filters = {
            "svg": "SVG Image (*.svg)",
            "png": "PNG Image (*.png)",
            "pdf": "PDF Document (*.pdf)",
        }

        file_name, _ = (
            QFileDialog.getSaveFileName(
                self,
                f"Export Graph {export_type.upper()}",
                f"jsonify-graph.{export_type}",
                filters[export_type],
            )
        )

        if not file_name:
            return

        self.graph_export_requested.emit(
            file_name
        )

    def show_export_success(
        self,
        file_name: str,
    ) -> None:
        """Show graph-export success."""

        self._status_label.setText(
            f"Graph exported: {file_name}"
        )

    def show_export_error(
        self,
        message: str,
    ) -> None:
        """Show graph-export failure."""

        QMessageBox.critical(
            self,
            "Export",
            message,
        )

    def _show_error(
        self,
        error: ExportError,
    ) -> None:
        """Display an export error."""

        QMessageBox.critical(
            self,
            "Export",
            str(error),
        )