"""Developer tools panel: JWT, Base64, escaping, timestamps, UUIDs, hashes."""

from __future__ import annotations

import json
from collections.abc import Callable

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from jsonify.core.devtools import (
    DevToolError,
    base64_decode,
    base64_encode,
    compute_hashes,
    convert_timestamp,
    decode_jwt,
    describe_uuid,
    find_uuids,
    generate_uuids,
    json_escape,
    json_unescape,
)
from jsonify.ui.constants import MONOSPACE_FONT


def _mono(edit: QPlainTextEdit) -> QPlainTextEdit:
    edit.setFont(QFont(MONOSPACE_FONT))
    return edit


class _ToolPage(QWidget):
    """Input box + action buttons + read-only output, shared by every tool."""

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout = QVBoxLayout(self)

        self.input = _mono(QPlainTextEdit())
        self.input.setPlaceholderText(placeholder)
        self._layout.addWidget(self.input, 1)

        self._buttons = QHBoxLayout()
        self._layout.addLayout(self._buttons)

        self.output = _mono(QPlainTextEdit())
        self.output.setReadOnly(True)
        self._layout.addWidget(self.output, 2)

        copy_button = QPushButton("Copy Output")
        copy_button.clicked.connect(
            lambda: QApplication.clipboard().setText(self.output.toPlainText())
        )
        self._buttons_tail = copy_button

    def add_action(self, label: str, handler: Callable[[], None]) -> QPushButton:
        button = QPushButton(label)
        button.clicked.connect(handler)
        self._buttons.addWidget(button)
        return button

    def finish_buttons(self) -> None:
        self._buttons.addStretch(1)
        self._buttons.addWidget(self._buttons_tail)

    def run(self, action: Callable[[str], str]) -> None:
        """Run ``action`` on the input text and show its result or error."""

        try:
            self.output.setPlainText(action(self.input.toPlainText()))
        except DevToolError as error:
            QMessageBox.warning(self, "Developer Tools", str(error))


class DevToolsView(QWidget):
    """Independent utilities that don't depend on the loaded document."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        title = QLabel("Developer Tools")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        layout.addWidget(title)

        note = QLabel("Everything here runs locally — nothing is sent anywhere.")
        layout.addWidget(note)

        tabs = QTabWidget()
        tabs.addTab(self._build_jwt(), "JWT")
        tabs.addTab(self._build_base64(), "Base64")
        tabs.addTab(self._build_escape(), "Escape")
        tabs.addTab(self._build_timestamp(), "Timestamp")
        tabs.addTab(self._build_uuid(), "UUID")
        tabs.addTab(self._build_hash(), "Hash")
        layout.addWidget(tabs, 1)

    # -----------------------------------------------------------------

    def _build_jwt(self) -> QWidget:
        page = _ToolPage("Paste a JWT (with or without 'Bearer ')...")

        def decode(text: str) -> str:
            info = decode_jwt(text)
            lines = ["HEADER", json.dumps(info.header, indent=2), "", "PAYLOAD"]
            lines.append(json.dumps(info.payload, indent=2, ensure_ascii=False))
            if info.claims:
                lines += ["", "TIME CLAIMS (UTC)"]
                lines += [f"  {label}: {value}" for label, value in info.claims.items()]
            if info.expired is not None:
                lines.append("  Status: " + ("EXPIRED" if info.expired else "not expired"))
            lines += [
                "",
                "Signature is NOT verified — decoding happens locally and no secret is used.",
            ]
            return "\n".join(lines)

        page.add_action("Decode", lambda: page.run(decode))
        page.finish_buttons()
        return page

    def _build_base64(self) -> QWidget:
        page = _ToolPage("Text to encode, or Base64 to decode...")
        url_safe = QCheckBox("URL-safe")
        page._buttons.addWidget(url_safe)
        page.add_action(
            "Encode", lambda: page.run(lambda t: base64_encode(t, url_safe=url_safe.isChecked()))
        )
        page.add_action(
            "Decode", lambda: page.run(lambda t: base64_decode(t, url_safe=url_safe.isChecked()))
        )
        page.finish_buttons()
        return page

    def _build_escape(self) -> QWidget:
        page = _ToolPage("Text to escape, or an escaped JSON string to unescape...")
        page.add_action("Escape", lambda: page.run(json_escape))
        page.add_action("Unescape", lambda: page.run(json_unescape))
        page.finish_buttons()
        return page

    def _build_timestamp(self) -> QWidget:
        page = _ToolPage("Unix seconds, Unix milliseconds, or an ISO-8601 date...")

        def convert(text: str) -> str:
            info = convert_timestamp(text)
            return (
                f"Detected as:   {info.detected_as}\n"
                f"Unix seconds:  {info.unix_seconds}\n"
                f"Unix millis:   {info.unix_milliseconds}\n"
                f"ISO-8601 UTC:  {info.iso_utc}"
            )

        page.add_action("Convert", lambda: page.run(convert))
        page.finish_buttons()
        return page

    def _build_uuid(self) -> QWidget:
        page = _ToolPage("Paste text to find UUIDs in, or one UUID to inspect...")

        count = QSpinBox()
        count.setRange(1, 100)
        count.setValue(1)
        page._buttons.addWidget(QLabel("Count:"))
        page._buttons.addWidget(count)

        page.add_action(
            "Generate v4",
            lambda: page.output.setPlainText("\n".join(generate_uuids(count.value(), version=4))),
        )
        page.add_action(
            "Generate v1",
            lambda: page.output.setPlainText("\n".join(generate_uuids(count.value(), version=1))),
        )

        def find(text: str) -> str:
            found = find_uuids(text)
            if not found:
                raise DevToolError("No UUIDs found.")
            return "\n".join(describe_uuid(uuid_text) for uuid_text in found)

        page.add_action("Find / Inspect", lambda: page.run(find))
        page.finish_buttons()
        return page

    def _build_hash(self) -> QWidget:
        page = _ToolPage("Text to hash (UTF-8)...")

        def hash_text(text: str) -> str:
            return "\n".join(f"{name:<9} {value}" for name, value in compute_hashes(text).items())

        page.add_action("Hash", lambda: page.run(hash_text))
        page.finish_buttons()
        return page
