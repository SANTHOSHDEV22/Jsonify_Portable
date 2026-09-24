"""API client user-interface widget."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.api_request import AUTH_KINDS, SUPPORTED_METHODS, ApiAuth, ApiRequest
from jsonify.core.curl import CurlParseError, parse_curl, to_curl
from jsonify.core.request_codegen import SUPPORTED_REQUEST_LANGUAGES, generate_request_code
from jsonify.services.api_service import (
    ApiBodyError,
    ApiRequestError,
    ApiResponse,
    ApiService,
)
from jsonify.services.api_workspace_service import ApiWorkspaceService
from jsonify.ui.constants import MONOSPACE_FONT
from jsonify.ui.widgets.lazy_tree_view import LazyJsonTreeView

_AUTH_LABELS = {
    "none": "No Auth",
    "basic": "Basic",
    "bearer": "Bearer Token",
    "apikey": "API Key",
    "custom": "Custom Header",
}
_BODY_KINDS = ("none", "json", "form")
_BODY_LABELS = {"none": "None", "json": "JSON", "form": "Form (urlencoded)"}
_CODE_LABELS = {"python": "Python", "javascript": "JavaScript", "csharp": "C#", "java": "Java"}


_SENSITIVE_HEADER_HINTS = ("authorization", "api-key", "apikey", "x-api-key", "cookie", "token")


class _KeyValueTable(QWidget):
    """An editable two-column table: enable/disable, add, remove, and (for
    headers) mask sensitive-looking values until revealed."""

    def __init__(
        self,
        headers: tuple[str, str],
        parent: QWidget | None = None,
        *,
        mask_sensitive_values: bool = False,
    ) -> None:
        super().__init__(parent)

        self._mask_sensitive_values = mask_sensitive_values
        self._revealed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["", *headers])
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        buttons = QHBoxLayout()
        add_button = QPushButton("+ Add Row")
        add_button.clicked.connect(lambda: self._insert_row("", "", enabled=True))
        buttons.addWidget(add_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_selected)
        buttons.addWidget(remove_button)

        if mask_sensitive_values:
            self._reveal_button = QPushButton("Show Values")
            self._reveal_button.setCheckable(True)
            self._reveal_button.toggled.connect(self._set_revealed)
            buttons.addWidget(self._reveal_button)

        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.set_pairs([])

    def _insert_row(self, key: str, value: str, *, enabled: bool) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        check_item = QTableWidgetItem()
        check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        check_item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
        self._table.setItem(row, 0, check_item)

        self._table.setItem(row, 1, QTableWidgetItem(key))
        self._table.setItem(row, 2, QTableWidgetItem(self._display_value(key, value)))
        self._table.item(row, 2).setData(Qt.ItemDataRole.UserRole, value)

    def _display_value(self, key: str, value: str) -> str:
        if self._mask_sensitive_values and not self._revealed and self._is_sensitive(key):
            return "•" * max(8, min(len(value), 24))
        return value

    @staticmethod
    def _is_sensitive(key: str) -> bool:
        lowered = key.strip().casefold()
        return any(hint in lowered for hint in _SENSITIVE_HEADER_HINTS)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 2 or self._revealed or not self._mask_sensitive_values:
            return
        # The user edited a (possibly masked) value cell directly: treat the
        # typed text as the new real value.
        item.setData(Qt.ItemDataRole.UserRole, item.text())

    def _set_revealed(self, revealed: bool) -> None:
        self._revealed = revealed
        self._reveal_button.setText("Hide Values" if revealed else "Show Values")
        self._rebuild(self._all_rows())

    def _all_rows(self) -> list[tuple[str, str, bool]]:
        """Every row (including disabled ones) as (key, real value, enabled)."""

        rows: list[tuple[str, str, bool]] = []
        for row in range(self._table.rowCount()):
            check_item = self._table.item(row, 0)
            key_item = self._table.item(row, 1)
            value_item = self._table.item(row, 2)

            key = key_item.text().strip() if key_item else ""
            real_value = value_item.data(Qt.ItemDataRole.UserRole) if value_item else None
            value = (
                real_value if real_value is not None else (value_item.text() if value_item else "")
            )
            enabled = check_item is not None and check_item.checkState() == Qt.CheckState.Checked

            rows.append((key, value, enabled))
        return rows

    def _remove_selected(self) -> None:
        for row in sorted({index.row() for index in self._table.selectedIndexes()}, reverse=True):
            self._table.removeRow(row)

    def set_pairs(self, pairs: list[tuple[str, str]]) -> None:
        self._rebuild([(key, value, True) for key, value in pairs])

    def _rebuild(self, rows: list[tuple[str, str, bool]]) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for key, value, enabled in rows:
            self._insert_row(key, value, enabled=enabled)
        while self._table.rowCount() < 3:
            self._insert_row("", "", enabled=True)
        self._table.blockSignals(False)

    def pairs(self, *, include_disabled: bool = False) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for row in range(self._table.rowCount()):
            check_item = self._table.item(row, 0)
            if not include_disabled and (
                check_item is None or check_item.checkState() != Qt.CheckState.Checked
            ):
                continue

            key_item = self._table.item(row, 1)
            value_item = self._table.item(row, 2)
            key = key_item.text().strip() if key_item else ""
            if not key:
                continue

            real_value = value_item.data(Qt.ItemDataRole.UserRole) if value_item else None
            value = (
                real_value if real_value is not None else (value_item.text() if value_item else "")
            )
            result.append((key, value))
        return result


class _EnvironmentDialog(QDialog):
    """Edit the variables of each environment (Dev/Test/QA/Prod/...)."""

    def __init__(self, workspace: ApiWorkspaceService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Environment Variables")
        self.resize(520, 420)

        self._workspace = workspace
        self._environments = workspace.get_environments()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Use variables in requests as {{name}}, e.g. {{base_url}}/users."))

        self._combo = QComboBox()
        self._combo.addItems(list(self._environments))
        self._combo.currentTextChanged.connect(self._load_selected)
        layout.addWidget(self._combo)

        self._table = _KeyValueTable(("Variable", "Value"))
        layout.addWidget(self._table, 1)

        buttons = QHBoxLayout()
        add_env = QPushButton("New Environment...")
        add_env.clicked.connect(self._add_environment)
        buttons.addWidget(add_env)
        buttons.addStretch(1)
        save = QPushButton("Save")
        save.clicked.connect(self._save_and_close)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        self._current = self._combo.currentText()
        self._load_selected(self._current)

    def _load_selected(self, name: str) -> None:
        self._stash_current()
        self._current = name
        self._table.set_pairs(list(self._environments.get(name, {}).items()))

    def _stash_current(self) -> None:
        if getattr(self, "_current", None):
            self._environments[self._current] = dict(self._table.pairs())

    def _add_environment(self) -> None:
        name, ok = QInputDialog.getText(self, "New Environment", "Environment name:")
        name = name.strip()
        if ok and name and name not in self._environments:
            self._stash_current()
            self._environments[name] = {}
            self._combo.addItem(name)
            self._combo.setCurrentText(name)

    def _save_and_close(self) -> None:
        self._stash_current()
        for name, variables in self._environments.items():
            self._workspace.set_environment(name, variables)
        self.accept()


class _CodeDialog(QDialog):
    """Show a generated request snippet in a chosen language."""

    def __init__(self, request: ApiRequest, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Request Code")
        self.resize(640, 460)
        self._request = request

        layout = QVBoxLayout(self)
        self._combo = QComboBox()
        for language in SUPPORTED_REQUEST_LANGUAGES:
            self._combo.addItem(_CODE_LABELS[language], language)
        self._combo.currentIndexChanged.connect(self._refresh)
        layout.addWidget(self._combo)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont(MONOSPACE_FONT))
        layout.addWidget(self._output, 1)

        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(
            lambda: QApplication.clipboard().setText(self._output.toPlainText())
        )
        layout.addWidget(copy_button, alignment=Qt.AlignmentFlag.AlignRight)

        self._refresh()

    def _refresh(self) -> None:
        self._output.setPlainText(generate_request_code(self._request, self._combo.currentData()))


class ApiView(QWidget):
    """Widget for building API requests and inspecting responses."""

    response_loaded = Signal(object)
    send_to_diff = Signal(str, bool)
    """Emitted with (response_body_text, is_old) when "Send to Diff" is clicked."""

    def __init__(
        self,
        api_service: ApiService | None = None,
        workspace_service: ApiWorkspaceService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._api_service = api_service if api_service is not None else ApiService()
        self._workspace = (
            workspace_service if workspace_service is not None else ApiWorkspaceService()
        )

        self._response: ApiResponse | None = None

        self._setup_ui()
        self._refresh_environments()
        self._refresh_history()
        self._refresh_collections()

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("API Client")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        outer = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(self._create_sidebar())
        outer.addWidget(self._create_main_panel())
        outer.setStretchFactor(0, 0)
        outer.setStretchFactor(1, 1)
        outer.setSizes([200, 800])
        layout.addWidget(outer, 1)

    def _create_sidebar(self) -> QWidget:
        tabs = QTabWidget()

        history_panel = QWidget()
        history_layout = QVBoxLayout(history_panel)
        self._history_list = QListWidget()
        self._history_list.itemActivated.connect(self._load_history_item)
        history_layout.addWidget(self._history_list)
        clear_history = QPushButton("Clear History")
        clear_history.clicked.connect(self._clear_history)
        history_layout.addWidget(clear_history)
        tabs.addTab(history_panel, "History")

        collections_panel = QWidget()
        collections_layout = QVBoxLayout(collections_panel)
        self._collections_tree = QTreeWidget()
        self._collections_tree.setHeaderHidden(True)
        self._collections_tree.itemActivated.connect(self._load_collection_item)
        collections_layout.addWidget(self._collections_tree)
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._delete_collection_item)
        collections_layout.addWidget(delete_button)
        tabs.addTab(collections_panel, "Collections")

        return tabs

    def _create_main_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        env_row = QHBoxLayout()
        env_row.addWidget(QLabel("Environment:"))
        self._env_combo = QComboBox()
        self._env_combo.currentTextChanged.connect(self._workspace.set_active_environment)
        env_row.addWidget(self._env_combo)
        edit_env = QPushButton("Variables...")
        edit_env.clicked.connect(self._edit_environments)
        env_row.addWidget(edit_env)
        env_row.addStretch(1)
        layout.addLayout(env_row)

        request_bar = QHBoxLayout()
        self._method_combo = QComboBox()
        self._method_combo.addItems(list(SUPPORTED_METHODS))
        request_bar.addWidget(self._method_combo)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("{{base_url}}/users  or  https://api.example.com/users")
        request_bar.addWidget(self._url_input, 1)

        self._send_button = QPushButton("Send")
        self._send_button.clicked.connect(self._send_request)
        request_bar.addWidget(self._send_button)
        layout.addLayout(request_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._create_request_tabs())
        splitter.addWidget(self._create_response_tabs())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self._status_label = QLabel("Ready")
        layout.addWidget(self._status_label)

        layout.addLayout(self._create_action_row())

        self._method_combo.currentTextChanged.connect(self._update_body_state)
        self._url_input.returnPressed.connect(self._send_request)
        self._update_body_state(self._method_combo.currentText())

        return panel

    def _create_request_tabs(self) -> QTabWidget:
        tabs = QTabWidget()

        self._params_table = _KeyValueTable(("Parameter", "Value"))
        tabs.addTab(self._params_table, "Params")

        self._headers_table = _KeyValueTable(("Header", "Value"), mask_sensitive_values=True)
        tabs.addTab(self._headers_table, "Headers")

        tabs.addTab(self._create_auth_tab(), "Auth")
        tabs.addTab(self._create_body_tab(), "Body")
        return tabs

    def _create_auth_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self._auth_combo = QComboBox()
        for kind in AUTH_KINDS:
            self._auth_combo.addItem(_AUTH_LABELS[kind], kind)
        layout.addWidget(self._auth_combo)

        self._auth_stack = QStackedWidget()
        layout.addWidget(self._auth_stack, 1)

        def page(rows: list[tuple[str, QWidget]]) -> QWidget:
            widget = QWidget()
            form = QFormLayout(widget)
            for label, field in rows:
                form.addRow(label, field)
            return widget

        self._basic_user = QLineEdit()
        self._basic_pass = QLineEdit()
        self._basic_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._bearer_token = QLineEdit()
        self._key_name = QLineEdit()
        self._key_value = QLineEdit()
        self._key_in = QComboBox()
        self._key_in.addItems(["header", "query"])
        self._custom_name = QLineEdit()
        self._custom_value = QLineEdit()

        self._auth_stack.addWidget(QLabel("This request does not use authentication."))
        self._auth_stack.addWidget(
            page([("Username", self._basic_user), ("Password", self._basic_pass)])
        )
        self._auth_stack.addWidget(page([("Token", self._bearer_token)]))
        self._auth_stack.addWidget(
            page([("Key", self._key_name), ("Value", self._key_value), ("Add to", self._key_in)])
        )
        self._auth_stack.addWidget(
            page([("Header", self._custom_name), ("Value", self._custom_value)])
        )

        self._auth_combo.currentIndexChanged.connect(self._auth_stack.setCurrentIndex)
        return panel

    def _create_body_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self._body_combo = QComboBox()
        for kind in _BODY_KINDS:
            self._body_combo.addItem(_BODY_LABELS[kind], kind)
        layout.addWidget(self._body_combo)

        self._body_stack = QStackedWidget()
        layout.addWidget(self._body_stack, 1)

        self._body_stack.addWidget(QLabel("This request has no body."))

        self._body_editor = QPlainTextEdit()
        self._body_editor.setPlaceholderText('{\n  "name": "Alice"\n}')
        self._body_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._body_editor.setFont(QFont(MONOSPACE_FONT))
        self._body_stack.addWidget(self._body_editor)

        self._form_table = _KeyValueTable(("Field", "Value"))
        self._body_stack.addWidget(self._form_table)

        self._body_combo.currentIndexChanged.connect(self._body_stack.setCurrentIndex)
        return panel

    def _create_response_tabs(self) -> QTabWidget:
        tabs = QTabWidget()

        # Reuses the same lazy tree used for loaded documents, rather than a
        # second JSON viewer, so a response gets the exact same expand /
        # collapse / copy-path / copy-pointer tooling.
        self._response_tree = LazyJsonTreeView()
        tabs.addTab(self._response_tree, "Response (Tree)")

        self._response_body = QPlainTextEdit()
        self._response_body.setReadOnly(True)
        self._response_body.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._response_body.setFont(QFont(MONOSPACE_FONT))
        tabs.addTab(self._response_body, "Response (Raw)")

        self._response_headers = QPlainTextEdit()
        self._response_headers.setReadOnly(True)
        self._response_headers.setFont(QFont(MONOSPACE_FONT))
        tabs.addTab(self._response_headers, "Response Headers")
        return tabs

    def _create_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        import_button = QPushButton("Import cURL...")
        import_button.clicked.connect(self._import_curl)
        row.addWidget(import_button)

        copy_curl = QPushButton("Copy as cURL")
        copy_curl.clicked.connect(self._copy_curl)
        row.addWidget(copy_curl)

        code_button = QPushButton("Code...")
        code_button.clicked.connect(self._show_code)
        row.addWidget(code_button)

        save_button = QPushButton("Save to Collection...")
        save_button.clicked.connect(self._save_to_collection)
        row.addWidget(save_button)

        compare_button = QPushButton("Compare Environments...")
        compare_button.clicked.connect(self._compare_environments)
        row.addWidget(compare_button)

        row.addStretch(1)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._clear)
        row.addWidget(clear_button)

        self._diff_old_button = QPushButton("Send to Diff (Old)")
        self._diff_old_button.setEnabled(False)
        self._diff_old_button.clicked.connect(lambda: self._send_to_diff(is_old=True))
        row.addWidget(self._diff_old_button)

        self._diff_new_button = QPushButton("Send to Diff (New)")
        self._diff_new_button.setEnabled(False)
        self._diff_new_button.clicked.connect(lambda: self._send_to_diff(is_old=False))
        row.addWidget(self._diff_new_button)

        self._load_button = QPushButton("Load Response into Jsonify")
        self._load_button.setEnabled(False)
        self._load_button.clicked.connect(self._load_response)
        row.addWidget(self._load_button)

        return row

    # -----------------------------------------------------------------
    # Request <-> UI
    # -----------------------------------------------------------------

    def build_request(self) -> ApiRequest:
        """Read the current UI state into an :class:`ApiRequest`."""

        return ApiRequest(
            method=self._method_combo.currentText(),
            url=self._url_input.text().strip(),
            params=self._params_table.pairs(),
            headers=self._headers_table.pairs(),
            auth=ApiAuth(
                kind=self._auth_combo.currentData(),
                username=self._basic_user.text(),
                password=self._basic_pass.text(),
                token=self._bearer_token.text(),
                key_name=self._key_name.text(),
                key_value=self._key_value.text(),
                key_in=self._key_in.currentText(),
                header_name=self._custom_name.text(),
                header_value=self._custom_value.text(),
            ),
            body_kind=self._body_combo.currentData(),
            body_text=self._body_editor.toPlainText(),
            form_fields=self._form_table.pairs(),
        )

    def set_json_body(self, text: str) -> None:
        """Put ``text`` into the JSON request body (e.g. from jq/JSONPath)."""

        self._body_combo.setCurrentIndex(_BODY_KINDS.index("json"))
        self._body_editor.setPlainText(text)

    def load_request(self, request: ApiRequest) -> None:
        """Populate the UI from a saved/imported request."""

        self._method_combo.setCurrentText(request.method.upper())
        self._url_input.setText(request.url)
        self._params_table.set_pairs(request.params)
        self._headers_table.set_pairs(request.headers)

        auth = request.auth
        self._auth_combo.setCurrentIndex(
            max(0, AUTH_KINDS.index(auth.kind)) if auth.kind in AUTH_KINDS else 0
        )
        self._basic_user.setText(auth.username)
        self._basic_pass.setText(auth.password)
        self._bearer_token.setText(auth.token)
        self._key_name.setText(auth.key_name)
        self._key_value.setText(auth.key_value)
        self._key_in.setCurrentText(auth.key_in)
        self._custom_name.setText(auth.header_name)
        self._custom_value.setText(auth.header_value)

        body_kind = request.body_kind if request.body_kind in _BODY_KINDS else "none"
        self._body_combo.setCurrentIndex(_BODY_KINDS.index(body_kind))
        self._body_editor.setPlainText(request.body_text)
        self._form_table.set_pairs(request.form_fields)

    def _active_variables(self) -> dict[str, str]:
        return self._workspace.get_environments().get(self._env_combo.currentText(), {})

    # -----------------------------------------------------------------
    # Sending
    # -----------------------------------------------------------------

    def _send_request(self) -> None:
        request = self.build_request()

        self._send_button.setEnabled(False)
        self._load_button.setEnabled(False)
        self._status_label.setText("Sending request...")

        try:
            response = self._api_service.send_request(request, self._active_variables())
        except (ApiRequestError, ApiBodyError) as error:
            QMessageBox.critical(self, "API Request", str(error))
            self._status_label.setText("Request failed.")
            return
        finally:
            self._send_button.setEnabled(True)

        self._response = response
        self._display_response(response)

        self._workspace.add_history(
            request,
            status_code=response.status_code,
            elapsed_ms=response.elapsed_ms,
            size_bytes=response.size_bytes,
            body=self._response_body.toPlainText(),
        )
        self._refresh_history()

    def _display_response(self, response: ApiResponse) -> None:
        if response.is_json and response.json_data is not None:
            body_text = json.dumps(response.json_data, indent=2, ensure_ascii=False)
            self._response_tree.set_payload(response.json_data)
        else:
            body_text = response.text
            self._response_tree.clear_payload()

        self._response_body.setPlainText(body_text)
        self._response_headers.setPlainText(
            "\n".join(f"{key}: {value}" for key, value in sorted(response.headers.items()))
        )

        self._status_label.setText(
            f"{response.status_code} {response.reason_phrase}   |   "
            f"{response.elapsed_ms:.0f} ms   |   {_format_size(response.size_bytes)}   |   "
            f"{response.content_type or 'unknown content type'}"
        )

        self._load_button.setEnabled(response.is_json)
        self._diff_old_button.setEnabled(True)
        self._diff_new_button.setEnabled(True)

    def _send_to_diff(self, *, is_old: bool) -> None:
        if self._response is None:
            return
        self.send_to_diff.emit(self._response_body.toPlainText(), is_old)

    def _load_response(self) -> None:
        if self._response is None:
            return

        if not self._response.is_json:
            QMessageBox.warning(self, "API Client", "The API response is not JSON.")
            return

        self.response_loaded.emit(self._response.json_data)
        self._status_label.setText(
            f"{self._response.status_code} {self._response.reason_phrase} "
            "| Response loaded into Jsonify."
        )

    # -----------------------------------------------------------------
    # cURL / code
    # -----------------------------------------------------------------

    def _import_curl(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "Import cURL", "Paste a cURL command:")
        if not ok or not text.strip():
            return

        try:
            request = parse_curl(text)
        except CurlParseError as error:
            QMessageBox.critical(self, "Import cURL", str(error))
            return

        self.load_request(request)
        self._status_label.setText("cURL command imported.")

    def _copy_curl(self) -> None:
        QApplication.clipboard().setText(to_curl(self.build_request()))
        self._status_label.setText("cURL command copied to the clipboard.")

    def _show_code(self) -> None:
        _CodeDialog(self.build_request(), self).exec()

    # -----------------------------------------------------------------
    # Environments
    # -----------------------------------------------------------------

    def _refresh_environments(self) -> None:
        self._env_combo.blockSignals(True)
        self._env_combo.clear()
        self._env_combo.addItems(list(self._workspace.get_environments()))
        self._env_combo.setCurrentText(self._workspace.get_active_environment())
        self._env_combo.blockSignals(False)

    def _edit_environments(self) -> None:
        _EnvironmentDialog(self._workspace, self).exec()
        self._refresh_environments()

    def _compare_environments(self) -> None:
        names = list(self._workspace.get_environments())
        if len(names) < 2:
            QMessageBox.information(
                self, "Compare Environments", "Define at least two environments."
            )
            return

        first, ok = QInputDialog.getItem(
            self, "Compare Environments", "First environment:", names, 0, False
        )
        if not ok:
            return
        second, ok = QInputDialog.getItem(
            self,
            "Compare Environments",
            "Second environment:",
            names,
            min(1, len(names) - 1),
            False,
        )
        if not ok:
            return

        environments = self._workspace.get_environments()

        try:
            result = self._api_service.compare_environments(
                self.build_request(), environments[first], environments[second]
            )
        except (ApiRequestError, ApiBodyError) as error:
            QMessageBox.critical(self, "Compare Environments", str(error))
            return

        def body(response: ApiResponse) -> str:
            if response.is_json:
                return json.dumps(response.json_data, indent=2, ensure_ascii=False)
            return response.text

        self.send_to_diff.emit(body(result.first), True)
        self.send_to_diff.emit(body(result.second), False)

        self._status_label.setText(
            f"{first}: {result.first.status_code} vs {second}: {result.second.status_code} — "
            f"{len(result.differences)} difference(s). Sent to the Diff tab; press Compare there."
        )

    # -----------------------------------------------------------------
    # History / collections
    # -----------------------------------------------------------------

    def _refresh_history(self) -> None:
        self._history_list.clear()
        for entry in self._workspace.get_history():
            request = ApiRequest.from_dict(entry.get("request", {}))
            item = QListWidgetItem(f"{entry.get('status', '?')}  {request.method}  {request.url}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._history_list.addItem(item)

    def _load_history_item(self, item: QListWidgetItem) -> None:
        entry = item.data(Qt.ItemDataRole.UserRole)
        self.load_request(ApiRequest.from_dict(entry.get("request", {})))
        self._response_body.setPlainText(str(entry.get("body", "")))
        self._status_label.setText(
            f"History: {entry.get('status')} | {entry.get('elapsed_ms')} ms | "
            f"{_format_size(int(entry.get('size_bytes', 0)))} | {entry.get('timestamp', '')}"
        )

    def _clear_history(self) -> None:
        self._workspace.clear_history()
        self._refresh_history()

    def _refresh_collections(self) -> None:
        """Rebuild the collections tree.

        A collection name containing ``/`` (e.g. ``E-Commerce/Users``) is
        shown as nested folders rather than one flat entry, so requests can
        be grouped the same way a Postman-style collection would be.
        """

        self._collections_tree.clear()
        folder_items: dict[tuple[str, ...], QTreeWidgetItem] = {}

        def folder_for(parts: tuple[str, ...]) -> QTreeWidgetItem | None:
            if not parts:
                return None
            if parts in folder_items:
                return folder_items[parts]

            parent_widget = folder_for(parts[:-1])
            item = QTreeWidgetItem([parts[-1]])
            item.setData(0, Qt.ItemDataRole.UserRole, {"collection": "/".join(parts)})
            if parent_widget is None:
                self._collections_tree.addTopLevelItem(item)
            else:
                parent_widget.addChild(item)
            item.setExpanded(True)
            folder_items[parts] = item
            return item

        for collection, items in sorted(self._workspace.get_collections().items()):
            parts = tuple(p for p in collection.split("/") if p)
            parent = folder_for(parts) if parts else folder_for(("(unnamed)",))

            for saved in items:
                child = QTreeWidgetItem([str(saved.get("name", "request"))])
                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {
                        "collection": collection,
                        "name": saved.get("name"),
                        "request": saved.get("request"),
                    },
                )
                if parent is None:
                    self._collections_tree.addTopLevelItem(child)
                else:
                    parent.addChild(child)

    def _save_to_collection(self) -> None:
        existing = sorted(self._workspace.get_collections())
        if existing:
            collection, ok = QInputDialog.getItem(
                self,
                "Save to Collection",
                "Collection (use 'Folder/Subfolder' to nest; type a new name to create one):",
                existing,
                0,
                True,
            )
        else:
            collection, ok = QInputDialog.getText(
                self, "Save to Collection", "Collection name (use 'Folder/Subfolder' to nest):"
            )
        if not ok or not collection.strip():
            return

        name, ok = QInputDialog.getText(self, "Save to Collection", "Request name:")
        if not ok or not name.strip():
            return

        self._workspace.save_to_collection(collection.strip(), name.strip(), self.build_request())
        self._refresh_collections()

    def _load_collection_item(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("request"):
            self.load_request(ApiRequest.from_dict(data["request"]))

    def _delete_collection_item(self) -> None:
        item = self._collections_tree.currentItem()
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        if not data or not data.get("name"):
            return
        self._workspace.delete_from_collection(data["collection"], data["name"])
        self._refresh_collections()

    # -----------------------------------------------------------------
    # Misc
    # -----------------------------------------------------------------

    def _update_body_state(self, method: str) -> None:
        """Body editing is only meaningful for methods that carry a body."""

        self._body_combo.setEnabled(method in {"POST", "PUT", "PATCH", "DELETE"})

    def _clear(self) -> None:
        self.load_request(ApiRequest())
        self._response_body.clear()
        self._response_headers.clear()
        self._response_tree.clear_payload()
        self._response = None
        self._load_button.setEnabled(False)
        self._diff_old_button.setEnabled(False)
        self._diff_new_button.setEnabled(False)
        self._status_label.setText("Ready")


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"
