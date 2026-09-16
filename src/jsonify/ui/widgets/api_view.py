"""API Response Viewer user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.models import JSONValue
from jsonify.services.api_service import (
    ApiBodyError,
    ApiRequestError,
    ApiResponse,
    ApiService,
)
from jsonify.ui.constants import MONOSPACE_FONT


class ApiView(QWidget):
    """Widget for sending API requests and inspecting responses."""

    response_loaded = Signal(object)

    def __init__(
        self,
        api_service: ApiService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._api_service = (
            api_service
            if api_service is not None
            else ApiService()
        )

        self._response: ApiResponse | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the API Response Viewer interface."""

        layout = QVBoxLayout(self)

        title = QLabel(
            "API Response Viewer"
        )

        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)

        title.setFont(title_font)

        layout.addWidget(title)

        description = QLabel(
            "Send an HTTP request, inspect the response, "
            "and load JSON responses into Jsonify."
        )

        description.setWordWrap(True)

        layout.addWidget(description)

        request_bar = QHBoxLayout()

        self._method_combo = QComboBox()

        self._method_combo.addItems(
            [
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            ]
        )

        self._url_input = QLineEdit()

        self._url_input.setPlaceholderText(
            "https://api.example.com/users"
        )

        self._send_button = QPushButton(
            "Send"
        )

        self._send_button.clicked.connect(
            self._send_request
        )

        request_bar.addWidget(
            self._method_combo
        )

        request_bar.addWidget(
            self._url_input,
            1,
        )

        request_bar.addWidget(
            self._send_button
        )

        layout.addLayout(
            request_bar
        )

        request_splitter = QSplitter()

        request_tabs = QTabWidget()

        self._headers_table = (
            self._create_headers_table()
        )

        request_tabs.addTab(
            self._headers_table,
            "Headers",
        )

        self._body_editor = QPlainTextEdit()

        self._body_editor.setPlaceholderText(
            '{\n  "name": "Alice"\n}'
        )

        self._body_editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        self._body_editor.setFont(
            QFont(MONOSPACE_FONT)
        )

        request_tabs.addTab(
            self._body_editor,
            "JSON Body",
        )

        response_tabs = QTabWidget()

        self._response_body = QPlainTextEdit()
        self._response_body.setReadOnly(True)

        self._response_body.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        self._response_body.setFont(
            QFont(MONOSPACE_FONT)
        )

        response_tabs.addTab(
            self._response_body,
            "Response Body",
        )

        self._response_headers = (
            QPlainTextEdit()
        )

        self._response_headers.setReadOnly(
            True
        )

        self._response_headers.setFont(
            QFont(MONOSPACE_FONT)
        )

        response_tabs.addTab(
            self._response_headers,
            "Response Headers",
        )

        request_splitter.addWidget(
            request_tabs
        )

        request_splitter.addWidget(
            response_tabs
        )

        request_splitter.setStretchFactor(
            0,
            1,
        )

        request_splitter.setStretchFactor(
            1,
            1,
        )

        layout.addWidget(
            request_splitter,
            1,
        )

        bottom_layout = QHBoxLayout()

        self._status_label = QLabel(
            "Ready"
        )

        self._load_button = QPushButton(
            "Load Response into Jsonify"
        )

        self._load_button.setEnabled(
            False
        )

        self._load_button.clicked.connect(
            self._load_response
        )

        clear_button = QPushButton(
            "Clear"
        )

        clear_button.clicked.connect(
            self._clear
        )

        bottom_layout.addWidget(
            self._status_label
        )

        bottom_layout.addStretch()

        bottom_layout.addWidget(
            clear_button
        )

        bottom_layout.addWidget(
            self._load_button
        )

        layout.addLayout(
            bottom_layout
        )

        self._method_combo.currentTextChanged.connect(
            self._update_body_state
        )

        self._url_input.returnPressed.connect(
            self._send_request
        )

        self._update_body_state(
            self._method_combo.currentText()
        )

    def _create_headers_table(
        self,
    ) -> QTableWidget:
        """Create editable request-header table."""

        table = QTableWidget(
            8,
            2,
        )

        table.setHorizontalHeaderLabels(
            [
                "Header",
                "Value",
            ]
        )

        header = table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        return table

    def _send_request(self) -> None:
        """Send the configured API request."""

        method = (
            self._method_combo
            .currentText()
        )

        url = (
            self._url_input
            .text()
            .strip()
        )

        headers = (
            self._collect_headers()
        )

        body = (
            self._body_editor
            .toPlainText()
        )

        if method in {
            "GET",
            "DELETE",
        }:
            body = ""

        self._send_button.setEnabled(
            False
        )

        self._load_button.setEnabled(
            False
        )

        self._status_label.setText(
            "Sending request..."
        )

        try:
            response = (
                self._api_service.send(
                    method=method,
                    url=url,
                    headers=headers,
                    body_text=body,
                )
            )

        except (
            ApiRequestError,
            ApiBodyError,
        ) as error:
            QMessageBox.critical(
                self,
                "API Request",
                str(error),
            )

            self._status_label.setText(
                "Request failed."
            )

            return

        finally:
            self._send_button.setEnabled(
                True
            )

        self._response = response

        self._display_response(
            response
        )

    def _display_response(
        self,
        response: ApiResponse,
    ) -> None:
        """Display an API response."""

        if (
            response.is_json
            and response.json_data is not None
        ):
            body_text = json.dumps(
                response.json_data,
                indent=2,
                ensure_ascii=False,
            )
        else:
            body_text = response.text

        self._response_body.setPlainText(
            body_text
        )

        header_text = "\n".join(
            f"{key}: {value}"
            for key, value
            in sorted(
                response.headers.items()
            )
        )

        self._response_headers.setPlainText(
            header_text
        )

        status = (
            f"{response.status_code} "
            f"{response.reason_phrase}"
        )

        self._status_label.setText(
            (
                f"{status}   |   "
                f"{response.elapsed_ms:.0f} ms   |   "
                f"{response.content_type or 'unknown content type'}"
            )
        )

        self._load_button.setEnabled(
            response.is_json
        )

    def _load_response(self) -> None:
        """Load the JSON response into the main Jsonify workspace."""

        if self._response is None:
            return

        if not self._response.is_json:
            QMessageBox.warning(
                self,
                "API Response Viewer",
                "The API response is not JSON.",
            )
            return

        self.response_loaded.emit(
            self._response.json_data
        )

        self._status_label.setText(
            (
                f"{self._response.status_code} "
                f"{self._response.reason_phrase} "
                "| Response loaded into Jsonify."
            )
        )

    def _collect_headers(
        self,
    ) -> dict[str, str]:
        """Collect request headers from the table."""

        headers: dict[str, str] = {}

        for row in range(
            self._headers_table.rowCount()
        ):
            key_item = (
                self._headers_table.item(
                    row,
                    0,
                )
            )

            value_item = (
                self._headers_table.item(
                    row,
                    1,
                )
            )

            if key_item is None:
                continue

            key = key_item.text().strip()

            if not key:
                continue

            value = (
                value_item.text().strip()
                if value_item is not None
                else ""
            )

            headers[key] = value

        return headers

    def _update_body_state(
        self,
        method: str,
    ) -> None:
        """Enable JSON body only for methods that normally use one."""

        enabled = method in {
            "POST",
            "PUT",
            "PATCH",
        }

        self._body_editor.setEnabled(
            enabled
        )

    def _clear(self) -> None:
        """Clear request and response data."""

        self._url_input.clear()

        self._body_editor.clear()

        self._response_body.clear()
        self._response_headers.clear()

        self._headers_table.clearContents()

        self._response = None

        self._load_button.setEnabled(
            False
        )

        self._status_label.setText(
            "Ready"
        )