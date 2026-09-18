"""Export user-interface widget for Jsonify."""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.models import JSONValue
from jsonify.services.export_service import ExportError, ExportService
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
            export_service if export_service is not None else ExportService()
        )

        self._payload: JSONValue | None = None
        self._masked_payload: JSONValue | None = None
        self._graph_view = None

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
            "Export JSON data or the current graph to a file."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        options = QHBoxLayout()
        options.addWidget(QLabel("Export:"))

        self._export_type = QComboBox()
        self._export_type.addItem("Formatted JSON", "json")
        self._export_type.addItem("Masked JSON", "masked_json")
        self._export_type.addItem("Graph SVG", "svg")
        self._export_type.addItem("Graph PNG", "png")
        self._export_type.addItem("Graph PDF", "pdf")
        options.addWidget(self._export_type)

        self._export_button = QPushButton("Export")
        self._export_button.clicked.connect(self._export)
        options.addWidget(self._export_button)
        options.addStretch()

        layout.addLayout(options)

        preview_label = QLabel("JSON Preview")
        preview_font = preview_label.font()
        preview_font.setBold(True)
        preview_label.setFont(preview_font)
        layout.addWidget(preview_label)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )
        self._preview.setFont(QFont(MONOSPACE_FONT))
        layout.addWidget(self._preview, 1)

        self._status_label = QLabel("Load JSON to begin.")
        layout.addWidget(self._status_label)

        self._export_type.currentIndexChanged.connect(
            self._refresh_preview
        )

    def set_payload(self, payload: JSONValue) -> None:
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

    def set_graph_view(self, graph_view) -> None:
        """Set the graph widget used for graph exports."""

        self._graph_view = graph_view

    def clear_payload(self) -> None:
        """Clear export data."""

        self._payload = None
        self._masked_payload = None
        self._preview.clear()
        self._status_label.setText("Load JSON to begin.")

    def _refresh_preview(self) -> None:
        """Refresh the JSON preview."""

        export_type = self._export_type.currentData()

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

        export_type = self._export_type.currentData()

        if export_type == "json":
            self._export_json()
            return

        if export_type == "masked_json":
            self._export_masked_json()
            return

        if export_type in {"svg", "png", "pdf"}:
            self._export_graph(export_type)

    @staticmethod
    def _windows_downloads_folder() -> Path:
        """Return the actual Windows Downloads known folder."""

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        folder_id_downloads = GUID(
            0x374DE290,
            0x123F,
            0x4565,
            (ctypes.c_ubyte * 8)(
                0x91,
                0x64,
                0x39,
                0xC4,
                0x92,
                0x5E,
                0x46,
                0x7B,
            ),
        )

        path_pointer = ctypes.c_wchar_p()

        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32

        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        shell32.SHGetKnownFolderPath.restype = wintypes.HRESULT

        result = shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id_downloads),
            0,
            None,
            ctypes.byref(path_pointer),
        )

        if result != 0 or not path_pointer.value:
            return Path.home() / "Downloads"

        try:
            return Path(path_pointer.value)
        finally:
            ole32.CoTaskMemFree(path_pointer)

    def _downloads_path(
        self,
        prefix: str,
        extension: str,
    ) -> Path:
        """Build a unique export path in the user's Downloads folder."""

        if os.name == "nt":
            try:
                downloads = self._windows_downloads_folder()
            except (AttributeError, OSError):
                downloads = Path.home() / "Downloads"
        else:
            downloads = Path.home() / "Downloads"

        downloads.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        return downloads / (
            f"{prefix}_{timestamp}.{extension}"
        )

    @staticmethod
    def _verify_export(file_path: Path) -> Path:
        """Verify that an export was actually written."""

        resolved_path = file_path.resolve()

        if not resolved_path.is_file():
            raise ExportError(
                "Export completed but the file was not created at: "
                f"{resolved_path}"
            )

        return resolved_path

    def _export_json(self) -> None:
        """Export the loaded JSON directly to Downloads."""

        if self._payload is None:
            QMessageBox.warning(
                self,
                "Export",
                "Load JSON before exporting.",
            )
            return

        file_path = self._downloads_path(
            "jsonify_export",
            "json",
        )

        try:
            self._export_service.export_json(
                self._payload,
                file_path,
            )
            path = self._verify_export(file_path)

        except (ExportError, OSError) as error:
            self._show_error(error)
            return

        self._status_label.setText(
            f"Exported successfully: {path}"
        )

    def _export_masked_json(self) -> None:
        """Export the latest masked JSON directly to Downloads."""

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

        file_path = self._downloads_path(
            "jsonify_masked",
            "json",
        )

        try:
            self._export_service.export_json(
                self._masked_payload,
                file_path,
            )
            path = self._verify_export(file_path)

        except (ExportError, OSError) as error:
            self._show_error(error)
            return

        self._status_label.setText(
            f"Exported successfully: {path}"
        )

    def _export_graph(
        self,
        export_type: str,
    ) -> None:
        """Export the current graph directly to Downloads."""

        if self._graph_view is None:
            self.show_export_error(
                "Graph view is not available for export."
            )
            return

        file_path = self._downloads_path(
            "jsonify_graph",
            export_type,
        )

        self._status_label.setText(
            f"Exporting graph to: {file_path.resolve()}"
        )
        self._export_button.setEnabled(False)

        def success(path: str) -> None:
            self._export_button.setEnabled(True)
            self.show_export_success(path)

        def failure(message: str) -> None:
            self._export_button.setEnabled(True)
            self._status_label.setText("Graph export failed.")
            self.show_export_error(message)

        self._graph_view.export_graph(
            str(file_path),
            on_success=success,
            on_error=failure,
        )

    def show_export_success(
        self,
        file_name: str,
    ) -> None:
        """Show graph-export success."""

        path = Path(file_name)

        if not path.is_file():
            self.show_export_error(
                "Graph export reported success, but the file "
                f"was not created at: {path.resolve()}"
            )
            return

        self._status_label.setText(
            f"Graph exported successfully: {path.resolve()}"
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
        error: Exception,
    ) -> None:
        """Display an export error."""

        QMessageBox.critical(
            self,
            "Export",
            str(error),
        )
