"""AI panel: an optional, bring-your-own-endpoint assistant.

No AI endpoint is configured by default and Jsonify ships no credentials
of its own. Every action here shows a plain "not configured" message and
makes no network call until the user has entered a base URL/model in the
Settings tab themselves — a hosted OpenAI-compatible provider, or a local
server such as Ollama/LM Studio. Generated queries are always shown for
review; nothing here runs a query or sends data automatically.
"""

from __future__ import annotations

import json

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.ai_prompts import (
    build_api_debug_prompt,
    build_query_generation_prompt,
    build_structure_analysis_prompt,
    build_test_case_prompt,
)
from jsonify.core.ai_provider import AiProviderConfig
from jsonify.core.anomalies import detect_anomalies
from jsonify.core.models import JSONValue
from jsonify.core.payload_generator import generate_payloads
from jsonify.core.profiling import profile_json
from jsonify.core.schema_inference import infer_schema
from jsonify.services.ai_config_service import AiConfigService
from jsonify.services.ai_service import AiNotConfiguredError, AiRequestError, AiService
from jsonify.ui.constants import MONOSPACE_FONT

_NOT_CONFIGURED_MESSAGE = (
    "No AI endpoint configured.\n\n"
    "Open the Settings tab and enter a base URL and model — either a "
    "hosted OpenAI-compatible provider, or a local server such as Ollama "
    "or LM Studio (e.g. http://localhost:11434/v1)."
)


def _mono(edit: QPlainTextEdit) -> QPlainTextEdit:
    edit.setFont(QFont(MONOSPACE_FONT))
    return edit


class AiView(QWidget):
    """Bring-your-own-endpoint AI assistant, off by default."""

    def __init__(
        self,
        config_service: AiConfigService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._config_service = config_service if config_service is not None else AiConfigService()
        self._payload: JSONValue | None = None

        tabs = QTabWidget()
        tabs.addTab(self._create_settings_tab(), "Settings")
        tabs.addTab(self._create_structure_tab(), "Structure Analysis")
        tabs.addTab(self._create_query_tab(), "Ask AI (Query)")
        tabs.addTab(self._create_debug_tab(), "API Debug")
        tabs.addTab(self._create_test_case_tab(), "Test Cases")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(tabs)

        self._refresh_status()

    # =================================================================
    # External wiring
    # =================================================================

    def set_payload(self, payload: JSONValue) -> None:
        """Called whenever the active document's JSON changes."""

        self._payload = payload

    def set_api_exchange(self, request_summary: str, response_summary: str) -> None:
        """Pre-fill the API Debug tab from the most recent API response."""

        self._debug_request.setPlainText(request_summary)
        self._debug_response.setPlainText(response_summary)

    # =================================================================
    # Settings tab
    # =================================================================

    def _create_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("AI Provider (OpenAI-compatible)")
        form = QFormLayout(group)

        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText(
            "https://api.openai.com/v1  or  http://localhost:11434/v1"
        )
        form.addRow("Base URL", self._base_url_edit)

        api_key_row = QHBoxLayout()
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("Optional — leave blank for local servers")
        api_key_row.addWidget(self._api_key_edit)
        show_key_button = QPushButton("Show")
        show_key_button.setCheckable(True)
        show_key_button.toggled.connect(self._toggle_api_key_visibility)
        api_key_row.addWidget(show_key_button)
        form.addRow("API Key", api_key_row)

        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("gpt-4o-mini, llama3, ...")
        form.addRow("Model", self._model_edit)

        layout.addWidget(group)

        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save_config)
        buttons.addWidget(save_button)

        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self._test_connection)
        buttons.addWidget(test_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._clear_config)
        buttons.addWidget(clear_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addWidget(
            QLabel(
                "Nothing on this page is sent anywhere until you click an "
                "action button elsewhere in this panel. Jsonify has no "
                "built-in AI credentials."
            ),
        )
        layout.addStretch(1)

        config = self._config_service.get_config()
        self._base_url_edit.setText(config.base_url)
        self._api_key_edit.setText(config.api_key)
        self._model_edit.setText(config.model)

        return page

    def _toggle_api_key_visibility(self, show: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
        self._api_key_edit.setEchoMode(mode)

    def _current_config(self) -> AiProviderConfig:
        return AiProviderConfig(
            base_url=self._base_url_edit.text().strip(),
            api_key=self._api_key_edit.text().strip(),
            model=self._model_edit.text().strip(),
        )

    def _save_config(self) -> None:
        self._config_service.set_config(self._current_config())
        self._refresh_status()

    def _clear_config(self) -> None:
        self._base_url_edit.clear()
        self._api_key_edit.clear()
        self._model_edit.clear()
        self._config_service.clear_config()
        self._refresh_status()

    def _refresh_status(self) -> None:
        config = self._config_service.get_config()
        if config.is_configured:
            self._status_label.setText(f"Configured: {config.model} @ {config.base_url}")
        else:
            self._status_label.setText("Not configured — AI features are inactive.")

    def _test_connection(self) -> None:
        service = AiService(self._current_config())

        if not service.is_configured():
            QMessageBox.information(self, "AI", _NOT_CONFIGURED_MESSAGE)
            return

        try:
            reply = service.complete(
                [{"role": "user", "content": "Reply with just the word: ok"}]
            )
        except (AiNotConfiguredError, AiRequestError) as error:
            QMessageBox.critical(self, "AI", str(error))
            return

        QMessageBox.information(self, "AI", f"Connection succeeded. Reply: {reply.strip()!r}")

    # =================================================================
    # Structure Analysis tab
    # =================================================================

    def _create_structure_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("Structural profile (computed locally, no AI needed):"))
        self._structure_profile = _mono(QPlainTextEdit())
        self._structure_profile.setReadOnly(True)
        layout.addWidget(self._structure_profile, 2)

        analyze_button = QPushButton("Analyze Structure with AI")
        analyze_button.clicked.connect(self._run_structure_analysis)
        layout.addWidget(analyze_button)

        layout.addWidget(QLabel("AI analysis:"))
        self._structure_result = _mono(QPlainTextEdit())
        self._structure_result.setReadOnly(True)
        layout.addWidget(self._structure_result, 2)

        return page

    def _run_structure_analysis(self) -> None:
        if self._payload is None:
            QMessageBox.warning(self, "AI", "Open a JSON document first.")
            return

        profile = profile_json(self._payload)
        anomalies = detect_anomalies(self._payload)

        summary = profile.summary_text()
        if anomalies:
            summary += "\n\nAnomalies detected:\n" + "\n".join(
                f"- [{a.category}] {a.path}: {a.message}" for a in anomalies
            )
        self._structure_profile.setPlainText(summary)

        service = AiService(self._config_service.get_config())
        if not service.is_configured():
            QMessageBox.information(self, "AI", _NOT_CONFIGURED_MESSAGE)
            return

        messages = build_structure_analysis_prompt(
            profile.summary_text(), [a.message for a in anomalies]
        )

        try:
            reply = service.complete(messages)
        except (AiNotConfiguredError, AiRequestError) as error:
            QMessageBox.critical(self, "AI", str(error))
            return

        self._structure_result.setPlainText(reply)

    # =================================================================
    # Ask AI (Query) tab
    # =================================================================

    def _create_query_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("Describe what you want in plain language:"))
        self._query_instruction = QLineEdit()
        self._query_instruction.setPlaceholderText("e.g. get every user's email address")
        layout.addWidget(self._query_instruction)

        row = QHBoxLayout()
        row.addWidget(QLabel("Query language:"))
        self._query_language = QComboBox()
        self._query_language.addItems(["jq", "jsonpath"])
        row.addWidget(self._query_language)
        row.addStretch(1)
        generate_button = QPushButton("Generate Expression")
        generate_button.clicked.connect(self._run_query_generation)
        row.addWidget(generate_button)
        layout.addLayout(row)

        layout.addWidget(
            QLabel(
                "Review the generated expression, then paste it into the "
                "jq or JSONPath tab yourself — it is never run automatically."
            )
        )
        self._query_result = _mono(QPlainTextEdit())
        self._query_result.setReadOnly(True)
        layout.addWidget(self._query_result, 1)

        return page

    def _run_query_generation(self) -> None:
        instruction = self._query_instruction.text().strip()
        if not instruction:
            QMessageBox.warning(self, "AI", "Describe what you want the query to do.")
            return

        if self._payload is None:
            QMessageBox.warning(self, "AI", "Open a JSON document first.")
            return

        service = AiService(self._config_service.get_config())
        if not service.is_configured():
            QMessageBox.information(self, "AI", _NOT_CONFIGURED_MESSAGE)
            return

        sample_summary = profile_json(self._payload).summary_text()
        language = self._query_language.currentText()
        messages = build_query_generation_prompt(instruction, sample_summary, language)

        try:
            reply = service.complete(messages)
        except (AiNotConfiguredError, AiRequestError) as error:
            QMessageBox.critical(self, "AI", str(error))
            return

        self._query_result.setPlainText(reply)

    # =================================================================
    # API Debug tab
    # =================================================================

    def _create_debug_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("Request summary:"))
        self._debug_request = _mono(QPlainTextEdit())
        layout.addWidget(self._debug_request, 1)

        layout.addWidget(QLabel("Response summary:"))
        self._debug_response = _mono(QPlainTextEdit())
        layout.addWidget(self._debug_response, 1)

        explain_button = QPushButton("Explain with AI")
        explain_button.clicked.connect(self._run_api_debug)
        layout.addWidget(explain_button)

        self._debug_result = _mono(QPlainTextEdit())
        self._debug_result.setReadOnly(True)
        layout.addWidget(self._debug_result, 1)

        return page

    def _run_api_debug(self) -> None:
        request_summary = self._debug_request.toPlainText().strip()
        response_summary = self._debug_response.toPlainText().strip()

        if not request_summary or not response_summary:
            QMessageBox.warning(
                self, "AI", "Fill in both the request and response summary."
            )
            return

        service = AiService(self._config_service.get_config())
        if not service.is_configured():
            QMessageBox.information(self, "AI", _NOT_CONFIGURED_MESSAGE)
            return

        messages = build_api_debug_prompt(request_summary, response_summary)

        try:
            reply = service.complete(messages)
        except (AiNotConfiguredError, AiRequestError) as error:
            QMessageBox.critical(self, "AI", str(error))
            return

        self._debug_result.setPlainText(reply)

    # =================================================================
    # Test Cases tab
    # =================================================================

    def _create_test_case_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(
            QLabel("Deterministic sample payloads, generated locally from the schema:")
        )
        row = QHBoxLayout()
        row.addWidget(QLabel("Count:"))
        self._test_case_count = QSpinBox()
        self._test_case_count.setRange(1, 20)
        self._test_case_count.setValue(3)
        row.addWidget(self._test_case_count)
        row.addStretch(1)
        generate_button = QPushButton("Generate Sample Payloads")
        generate_button.clicked.connect(self._run_payload_generation)
        row.addWidget(generate_button)
        layout.addLayout(row)

        self._test_case_output = _mono(QPlainTextEdit())
        self._test_case_output.setReadOnly(True)
        layout.addWidget(self._test_case_output, 1)

        ai_button = QPushButton("Suggest Edge Cases with AI")
        ai_button.clicked.connect(self._run_ai_test_cases)
        layout.addWidget(ai_button)

        self._test_case_ai_output = _mono(QPlainTextEdit())
        self._test_case_ai_output.setReadOnly(True)
        layout.addWidget(self._test_case_ai_output, 1)

        return page

    def _run_payload_generation(self) -> None:
        if self._payload is None:
            QMessageBox.warning(self, "AI", "Open a JSON document first.")
            return

        schema = infer_schema(self._payload)
        payloads = generate_payloads(schema, self._test_case_count.value())
        self._test_case_output.setPlainText(json.dumps(payloads, indent=2, ensure_ascii=False))

    def _run_ai_test_cases(self) -> None:
        if self._payload is None:
            QMessageBox.warning(self, "AI", "Open a JSON document first.")
            return

        service = AiService(self._config_service.get_config())
        if not service.is_configured():
            QMessageBox.information(self, "AI", _NOT_CONFIGURED_MESSAGE)
            return

        schema_summary = json.dumps(infer_schema(self._payload), indent=2, ensure_ascii=False)
        messages = build_test_case_prompt(schema_summary, self._test_case_count.value())

        try:
            reply = service.complete(messages)
        except (AiNotConfiguredError, AiRequestError) as error:
            QMessageBox.critical(self, "AI", str(error))
            return

        self._test_case_ai_output.setPlainText(reply)
