"""A JSON-aware code editor widget.

Provides the editing experience shared by every "paste/open JSON" surface in
Jsonify: a line-number gutter, JSON syntax highlighting, live-as-you-type
validation with an inline error marker, auto-indent, and matching-bracket
highlighting. Undo/redo come for free from ``QPlainTextEdit``.
"""

from __future__ import annotations

import json

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from jsonify.ui.constants import MONOSPACE_FONT

_OPEN_BRACKETS = "{["
_CLOSE_BRACKETS = "}]"
_MATCHING = {
    "{": "}",
    "[": "]",
    "}": "{",
    "]": "[",
}

# Debounce delay before re-validating after a keystroke, in milliseconds.
_VALIDATION_DELAY_MS = 250


class JsonSyntaxHighlighter(QSyntaxHighlighter):
    """Minimal, fast JSON syntax highlighter.

    Tokenizes each line independently (JSON has no multi-line string
    literals), so no block-state tracking is required.
    """

    def __init__(self, document: QTextDocument, theme: dict[str, str] | None = None) -> None:
        super().__init__(document)

        self._formats: dict[str, QTextCharFormat] = {}

        self.apply_theme(theme or {})

    def apply_theme(self, theme: dict[str, str]) -> None:
        """Update token colors from a theme's color map and re-highlight."""

        def make_format(color: str, bold: bool = False) -> QTextCharFormat:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            return fmt

        self._formats = {
            "key": make_format(theme.get("syntax.key", "#9CDCFE")),
            "string": make_format(theme.get("syntax.string", "#CE9178")),
            "number": make_format(theme.get("syntax.number", "#B5CEA8")),
            "keyword": make_format(theme.get("syntax.keyword", "#569CD6"), bold=True),
            "punctuation": make_format(theme.get("syntax.punctuation", "#D4D4D4")),
        }

        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt override)
        index = 0
        length = len(text)

        while index < length:
            char = text[index]

            if char in " \t\r\n":
                index += 1
                continue

            if char == '"':
                start = index
                index += 1
                while index < length:
                    if text[index] == "\\":
                        index += 2
                        continue
                    if text[index] == '"':
                        index += 1
                        break
                    index += 1

                # A string is a "key" when the next non-space char is ':'.
                lookahead = index
                while lookahead < length and text[lookahead] in " \t":
                    lookahead += 1

                is_key = lookahead < length and text[lookahead] == ":"

                self.setFormat(
                    start,
                    index - start,
                    self._formats["key" if is_key else "string"],
                )
                continue

            if char in "{}[],:":
                self.setFormat(index, 1, self._formats["punctuation"])
                index += 1
                continue

            if char in "-0123456789":
                start = index
                index += 1
                while index < length and (text[index].isdigit() or text[index] in ".eE+-"):
                    index += 1
                self.setFormat(start, index - start, self._formats["number"])
                continue

            if text[index : index + 4] in ("true", "null") or text[index : index + 5] == "false":
                for keyword in ("false", "true", "null"):
                    if text.startswith(keyword, index):
                        self.setFormat(index, len(keyword), self._formats["keyword"])
                        index += len(keyword)
                        break
                continue

            index += 1


class _LineNumberArea(QWidget):
    """Gutter widget that renders line numbers for a ``CodeEditor``."""

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override)
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """A ``QPlainTextEdit`` with line numbers, JSON highlighting, and
    live validation."""

    validationChanged = Signal(object)
    """Emits ``None`` when the current text is valid JSON, otherwise a
    ``json.JSONDecodeError``."""

    fileDropped = Signal(str)
    """Emitted with a local file path when a file is dropped onto the editor."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        font = self.font()
        font.setFamily(MONOSPACE_FONT)
        self.setFont(font)
        self.setTabStopDistance(20)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setAcceptDrops(True)

        self._highlighter = JsonSyntaxHighlighter(self.document())
        self._line_number_area = _LineNumberArea(self)
        self._last_error: json.JSONDecodeError | None = None

        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self._validate)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line_and_brackets)
        self.textChanged.connect(self._on_text_changed)

        self._update_line_number_area_width(0)
        self._highlight_current_line_and_brackets()

    # -----------------------------------------------------------------
    # Theming
    # -----------------------------------------------------------------

    def apply_theme(self, theme: dict[str, str]) -> None:
        """Re-color syntax highlighting for a new theme."""

        self._highlighter.apply_theme(theme)
        self._current_line_color = QColor(theme.get("editor.currentLine", "#2A2D2E"))
        self._error_line_color = QColor(theme.get("editor.errorLine", "#5A1D1D"))
        self._highlight_current_line_and_brackets()

    # -----------------------------------------------------------------
    # Line numbers
    # -----------------------------------------------------------------

    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        contents_rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(
                contents_rect.left(),
                contents_rect.top(),
                self.line_number_area_width(),
                contents_rect.height(),
            )
        )

    def paint_line_numbers(self, event: QPaintEvent) -> None:
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self.palette().window())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        error_line = self._last_error.lineno - 1 if self._last_error is not None else -1

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                text = str(block_number + 1)
                painter.setPen(
                    QColor("#F14C4C")
                    if block_number == error_line
                    else self.palette().text().color()
                )
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    text,
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    # -----------------------------------------------------------------
    # Current line + error + bracket-match highlighting
    # -----------------------------------------------------------------

    def _highlight_current_line_and_brackets(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []

        if not self.isReadOnly():
            current_line_color = getattr(self, "_current_line_color", QColor("#2A2D2E"))
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(current_line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)

        selections.extend(self._bracket_match_selections())

        if self._last_error is not None:
            error_line_color = getattr(self, "_error_line_color", QColor("#5A1D1D"))
            cursor = QTextCursor(self.document())
            block = self.document().findBlockByNumber(self._last_error.lineno - 1)
            if block.isValid():
                cursor.setPosition(block.position())
                cursor.movePosition(
                    QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor
                )
                error_selection = QTextEdit.ExtraSelection()
                error_selection.format.setUnderlineStyle(
                    QTextCharFormat.UnderlineStyle.WaveUnderline
                )
                error_selection.format.setUnderlineColor(QColor("#F14C4C"))
                error_selection.format.setBackground(error_line_color)
                error_selection.cursor = cursor
                selections.append(error_selection)

        self.setExtraSelections(selections)

    def _bracket_match_selections(self) -> list[QTextEdit.ExtraSelection]:
        cursor = self.textCursor()
        doc = self.document()
        text = doc.toPlainText()
        pos = cursor.position()

        for check_pos in (pos, pos - 1):
            if 0 <= check_pos < len(text) and text[check_pos] in _MATCHING:
                match_pos = self._find_matching_bracket(text, check_pos)
                if match_pos is not None:
                    return [
                        self._bracket_selection(check_pos),
                        self._bracket_selection(match_pos),
                    ]
        return []

    def _bracket_selection(self, position: int) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#515C6A"))
        selection.format.setFontWeight(QFont.Weight.Bold)
        cursor = QTextCursor(self.document())
        cursor.setPosition(position)
        cursor.setPosition(position + 1, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        return selection

    @staticmethod
    def _find_matching_bracket(text: str, start: int) -> int | None:
        opening = text[start] in _OPEN_BRACKETS
        target = _MATCHING[text[start]]
        step = 1 if opening else -1
        depth = 0
        index = start

        while 0 <= index < len(text):
            char = text[index]
            if char == text[start]:
                depth += 1
            elif char == target:
                depth -= 1
                if depth == 0:
                    return index
            index += step

        return None

    # -----------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------

    def _on_text_changed(self) -> None:
        self._validation_timer.start(_VALIDATION_DELAY_MS)

    def _validate(self) -> None:
        text = self.toPlainText()

        if not text.strip():
            self._last_error = None
            self.validationChanged.emit(None)
            self._highlight_current_line_and_brackets()
            return

        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            self._last_error = error
            self.validationChanged.emit(error)
        else:
            self._last_error = None
            self.validationChanged.emit(None)

        self._highlight_current_line_and_brackets()

    def validate_now(self) -> json.JSONDecodeError | None:
        """Force immediate (non-debounced) validation and return the error, if any."""

        self._validation_timer.stop()
        self._validate()
        return self._last_error

    # -----------------------------------------------------------------
    # Drag & drop file loading
    # -----------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 (Qt override)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 (Qt override)
        urls = event.mimeData().urls()

        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                event.acceptProposedAction()
                self.fileDropped.emit(local_path)
                return

        super().dropEvent(event)

    # -----------------------------------------------------------------
    # Auto-indent
    # -----------------------------------------------------------------

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._insert_auto_indented_newline()
            return

        super().keyPressEvent(event)

    def _insert_auto_indented_newline(self) -> None:
        cursor = self.textCursor()
        block_text = cursor.block().text()
        col = cursor.positionInBlock()
        before_cursor = block_text[:col]
        after_cursor = block_text[col:]

        current_indent = before_cursor[: len(before_cursor) - len(before_cursor.lstrip(" "))]

        opens_block = before_cursor.rstrip().endswith(("{", "["))
        closes_immediately = after_cursor.lstrip().startswith(("}", "]"))

        cursor.beginEditBlock()
        cursor.insertText("\n" + current_indent)

        if opens_block:
            cursor.insertText("  ")

            if closes_immediately:
                # Land the closing bracket on its own dedented line so the
                # cursor ends up on a fresh, correctly indented blank line
                # between the open and close brackets.
                closing_position = cursor.position()
                cursor.insertText("\n" + current_indent)
                cursor.setPosition(closing_position)

        cursor.endEditBlock()
        self.setTextCursor(cursor)
