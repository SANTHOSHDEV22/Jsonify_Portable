"""UI constants and styling for Jsonify."""

APP_NAME = "Jsonify"
APP_VERSION = "1.0.0"

WINDOW_TITLE = f"{APP_NAME} — JSON Payload Viewer"

DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900


# ---------------------------------------------------------------------
# Filtered view
# ---------------------------------------------------------------------

LEVEL_PLACEHOLDER = "-- choose key --"

FILTERED_VIEW_PLACEHOLDER = (
    "Pick a key at each level above, then click Show to display the matching JSON hierarchy."
)


# ---------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------

MESSAGE_NOTHING_TO_LOAD_TITLE = "Nothing to Load"
MESSAGE_NOTHING_TO_LOAD = "Paste a JSON payload into the editor first."

MESSAGE_INVALID_JSON_TITLE = "Invalid JSON"

MESSAGE_NO_JSON_TITLE = "No JSON Loaded"
MESSAGE_NO_JSON = "Paste and load a JSON payload first."

MESSAGE_NO_GRAPH_TITLE = "No Graph"
MESSAGE_NO_GRAPH = "Load a JSON payload first."


# ---------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------

EDITOR_PLACEHOLDER = "Paste JSON payloads here, then click 'Load JSON'..."

MONOSPACE_FONT = "Consolas"


# ---------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------

DARK_STYLESHEET = """
QMainWindow,
QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
}

QMenuBar {
    background-color: #2d2d30;
    color: #d4d4d4;
    border-bottom: 1px solid #3f3f46;
}

QMenuBar::item {
    padding: 4px 12px;
    border-right: 1px solid #3f3f46;
}

QMenuBar::item:selected {
    background-color: #3f3f46;
}

QMenu {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3f3f46;
}

QMenu::item:selected {
    background-color: #007acc;
}

QLabel {
    color: #d4d4d4;
}

QComboBox,
QPushButton,
QPlainTextEdit,
QTreeWidget,
QTreeView {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3f3f46;
    padding: 4px;
}

QPushButton {
    padding: 6px 14px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #3f3f46;
}

QPushButton:pressed {
    background-color: #007acc;
}

QTabWidget::pane {
    border: 1px solid #3f3f46;
}

QTabBar::tab {
    background-color: #2d2d30;
    color: #d4d4d4;
    padding: 6px 14px;
    border: 1px solid #3f3f46;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 2px solid #007acc;
}

QTreeWidget::item,
QTreeView::item {
    padding: 2px;
}

QTreeView::branch {
    background-color: #252526;
}

QHeaderView::section {
    background-color: #2d2d30;
    color: #d4d4d4;
    padding: 4px;
    border: none;
    border-right: 1px solid #3f3f46;
}
"""


LIGHT_STYLESHEET = """
QMainWindow,
QWidget {
    background-color: #ffffff;
    color: #1e1e1e;
}

QMenuBar {
    background-color: #f3f3f3;
    color: #1e1e1e;
    border-bottom: 1px solid #d4d4d4;
}

QMenuBar::item {
    padding: 4px 12px;
    border-right: 1px solid #d4d4d4;
}

QMenuBar::item:selected {
    background-color: #e0e0e0;
}

QMenu {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
}

QMenu::item:selected {
    background-color: #007acc;
    color: #ffffff;
}

QLabel {
    color: #1e1e1e;
}

QComboBox,
QPushButton,
QPlainTextEdit,
QTreeWidget,
QTreeView {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
    padding: 4px;
}

QPushButton {
    padding: 6px 14px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #e8e8e8;
}

QPushButton:pressed {
    background-color: #007acc;
    color: #ffffff;
}

QTabWidget::pane {
    border: 1px solid #c8c8c8;
}

QTabBar::tab {
    background-color: #f3f3f3;
    color: #1e1e1e;
    padding: 6px 14px;
    border: 1px solid #c8c8c8;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 2px solid #007acc;
}

QTreeWidget::item,
QTreeView::item {
    padding: 2px;
}

QTreeView::branch {
    background-color: #ffffff;
}

QHeaderView::section {
    background-color: #f3f3f3;
    color: #1e1e1e;
    padding: 4px;
    border: none;
    border-right: 1px solid #d4d4d4;
}
"""