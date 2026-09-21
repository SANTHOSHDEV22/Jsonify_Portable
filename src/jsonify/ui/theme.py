"""Jsonify's theme registry.

A ``Theme`` is a flat dict of color tokens plus a display name. The same
dict feeds two consumers: :func:`build_stylesheet` (which fills in the
Qt-widget QSS template below) and ``CodeEditor.apply_theme`` (which reads
the ``syntax.*`` / ``editor.*`` tokens directly for syntax highlighting).
"""

from __future__ import annotations

from dataclasses import dataclass

SYSTEM_THEME_ID = "system"


@dataclass(frozen=True)
class Theme:
    """A named, complete color palette for the whole application."""

    id: str
    name: str
    is_dark: bool
    colors: dict[str, str]


# -----------------------------------------------------------------------
# QSS template
#
# Tokens (no dots) are substituted via str.format(**colors); the dotted
# "syntax.*"/"editor.*" tokens in each theme's color dict are ignored here
# and consumed directly by CodeEditor instead.
# -----------------------------------------------------------------------

_QSS_TEMPLATE = """
QMainWindow, QWidget {{
    background-color: {bg};
    color: {fg};
}}

QMenuBar {{
    background-color: {bg_alt};
    color: {fg};
    border-bottom: 1px solid {border};
}}

QMenuBar::item {{
    padding: 4px 12px;
    border-right: 1px solid {border};
}}

QMenuBar::item:selected {{
    background-color: {hover};
}}

QMenu {{
    background-color: {panel};
    color: {fg};
    border: 1px solid {border};
}}

QMenu::item:selected {{
    background-color: {accent};
    color: {accent_fg};
}}

QLabel {{
    color: {fg};
}}

QComboBox,
QPushButton,
QPlainTextEdit,
QLineEdit,
QTreeWidget,
QTreeView,
QTableWidget,
QListWidget {{
    background-color: {panel};
    color: {fg};
    border: 1px solid {border};
    padding: 4px;
}}

QPushButton {{
    padding: 6px 14px;
    border-radius: 3px;
}}

QPushButton:hover {{
    background-color: {hover};
}}

QPushButton:pressed {{
    background-color: {accent};
    color: {accent_fg};
}}

QTabWidget::pane {{
    border: 1px solid {border};
}}

QTabBar::tab {{
    background-color: {bg_alt};
    color: {fg};
    padding: 6px 14px;
    border: 1px solid {border};
    border-bottom: none;
}}

QTabBar::tab:selected {{
    background-color: {bg};
    border-bottom: 2px solid {accent};
}}

QTreeWidget::item,
QTreeView::item,
QListWidget::item {{
    padding: 2px;
}}

QTreeWidget::item:selected,
QTreeView::item:selected,
QListWidget::item:selected {{
    background-color: {selection};
}}

QTreeView::branch {{
    background-color: {panel};
}}

QHeaderView::section {{
    background-color: {bg_alt};
    color: {fg};
    padding: 4px;
    border: none;
    border-right: 1px solid {border};
}}

QStatusBar {{
    background-color: {bg_alt};
    color: {fg};
    border-top: 1px solid {border};
}}

/* Activity bar: the narrow icon rail switching a document's tool sidebar */
QToolButton#activityBarButton {{
    background-color: {bg_alt};
    color: {fg};
    border: none;
    padding: 10px;
}}

QToolButton#activityBarButton:hover {{
    background-color: {hover};
}}

QToolButton#activityBarButton:checked {{
    background-color: {panel};
    border-left: 2px solid {accent};
}}

/* Command palette */
QDialog#commandPalette {{
    background-color: {panel};
    border: 1px solid {border};
}}

QDialog#commandPalette QLineEdit {{
    font-size: 14px;
    padding: 8px;
}}
"""


def build_stylesheet(theme: Theme) -> str:
    """Render this theme's QSS by filling in the shared template."""

    return _QSS_TEMPLATE.format(**theme.colors)


# -----------------------------------------------------------------------
# Built-in themes
# -----------------------------------------------------------------------

_DARK_PLUS = Theme(
    id="dark_plus",
    name="Dark+",
    is_dark=True,
    colors={
        "bg": "#1e1e1e",
        "bg_alt": "#2d2d30",
        "panel": "#252526",
        "border": "#3f3f46",
        "fg": "#d4d4d4",
        "accent": "#007acc",
        "accent_fg": "#ffffff",
        "hover": "#3f3f46",
        "selection": "#094771",
        "syntax.key": "#9CDCFE",
        "syntax.string": "#CE9178",
        "syntax.number": "#B5CEA8",
        "syntax.keyword": "#569CD6",
        "syntax.punctuation": "#D4D4D4",
        "editor.currentLine": "#2A2D2E",
        "editor.errorLine": "#5A1D1D",
    },
)

_LIGHT_PLUS = Theme(
    id="light_plus",
    name="Light+",
    is_dark=False,
    colors={
        "bg": "#ffffff",
        "bg_alt": "#f3f3f3",
        "panel": "#ffffff",
        "border": "#c8c8c8",
        "fg": "#1e1e1e",
        "accent": "#007acc",
        "accent_fg": "#ffffff",
        "hover": "#e8e8e8",
        "selection": "#add6ff",
        "syntax.key": "#0451A5",
        "syntax.string": "#A31515",
        "syntax.number": "#098658",
        "syntax.keyword": "#0000FF",
        "syntax.punctuation": "#1E1E1E",
        "editor.currentLine": "#EAEAEA",
        "editor.errorLine": "#FDE2E2",
    },
)

_MONOKAI = Theme(
    id="monokai",
    name="Monokai",
    is_dark=True,
    colors={
        "bg": "#272822",
        "bg_alt": "#1e1f1c",
        "panel": "#2d2e27",
        "border": "#3e3d32",
        "fg": "#f8f8f2",
        "accent": "#66d9ef",
        "accent_fg": "#272822",
        "hover": "#3e3d32",
        "selection": "#49483e",
        "syntax.key": "#66d9ef",
        "syntax.string": "#e6db74",
        "syntax.number": "#ae81ff",
        "syntax.keyword": "#f92672",
        "syntax.punctuation": "#f8f8f2",
        "editor.currentLine": "#3e3d32",
        "editor.errorLine": "#5c1f1f",
    },
)

_SOLARIZED_DARK = Theme(
    id="solarized_dark",
    name="Solarized Dark",
    is_dark=True,
    colors={
        "bg": "#002b36",
        "bg_alt": "#073642",
        "panel": "#073642",
        "border": "#586e75",
        "fg": "#839496",
        "accent": "#268bd2",
        "accent_fg": "#002b36",
        "hover": "#073642",
        "selection": "#094552",
        "syntax.key": "#268bd2",
        "syntax.string": "#2aa198",
        "syntax.number": "#6c71c4",
        "syntax.keyword": "#cb4b16",
        "syntax.punctuation": "#839496",
        "editor.currentLine": "#073642",
        "editor.errorLine": "#5c1f1f",
    },
)

_SOLARIZED_LIGHT = Theme(
    id="solarized_light",
    name="Solarized Light",
    is_dark=False,
    colors={
        "bg": "#fdf6e3",
        "bg_alt": "#eee8d5",
        "panel": "#eee8d5",
        "border": "#93a1a1",
        "fg": "#657b83",
        "accent": "#268bd2",
        "accent_fg": "#fdf6e3",
        "hover": "#eee8d5",
        "selection": "#d8d0b8",
        "syntax.key": "#268bd2",
        "syntax.string": "#2aa198",
        "syntax.number": "#6c71c4",
        "syntax.keyword": "#cb4b16",
        "syntax.punctuation": "#657b83",
        "editor.currentLine": "#eee8d5",
        "editor.errorLine": "#f2d6d3",
    },
)

_DRACULA = Theme(
    id="dracula",
    name="Dracula",
    is_dark=True,
    colors={
        "bg": "#282a36",
        "bg_alt": "#21222c",
        "panel": "#21222c",
        "border": "#44475a",
        "fg": "#f8f8f2",
        "accent": "#bd93f9",
        "accent_fg": "#282a36",
        "hover": "#44475a",
        "selection": "#44475a",
        "syntax.key": "#8be9fd",
        "syntax.string": "#f1fa8c",
        "syntax.number": "#bd93f9",
        "syntax.keyword": "#ff79c6",
        "syntax.punctuation": "#f8f8f2",
        "editor.currentLine": "#44475a",
        "editor.errorLine": "#5c1f1f",
    },
)

_NORD = Theme(
    id="nord",
    name="Nord",
    is_dark=True,
    colors={
        "bg": "#2e3440",
        "bg_alt": "#3b4252",
        "panel": "#3b4252",
        "border": "#4c566a",
        "fg": "#e5e9f0",
        "accent": "#88c0d0",
        "accent_fg": "#2e3440",
        "hover": "#434c5e",
        "selection": "#434c5e",
        "syntax.key": "#88c0d0",
        "syntax.string": "#a3be8c",
        "syntax.number": "#b48ead",
        "syntax.keyword": "#81a1c1",
        "syntax.punctuation": "#e5e9f0",
        "editor.currentLine": "#3b4252",
        "editor.errorLine": "#5c2626",
    },
)

_HIGH_CONTRAST = Theme(
    id="high_contrast",
    name="High Contrast",
    is_dark=True,
    colors={
        "bg": "#000000",
        "bg_alt": "#000000",
        "panel": "#000000",
        "border": "#ffffff",
        "fg": "#ffffff",
        "accent": "#1aebff",
        "accent_fg": "#000000",
        "hover": "#1aebff",
        "selection": "#1aebff",
        "syntax.key": "#ffcc00",
        "syntax.string": "#66ff66",
        "syntax.number": "#ffffff",
        "syntax.keyword": "#ff6666",
        "syntax.punctuation": "#ffffff",
        "editor.currentLine": "#1a1a1a",
        "editor.errorLine": "#660000",
    },
)

THEMES: dict[str, Theme] = {
    theme.id: theme
    for theme in (
        _DARK_PLUS,
        _LIGHT_PLUS,
        _MONOKAI,
        _SOLARIZED_DARK,
        _SOLARIZED_LIGHT,
        _DRACULA,
        _NORD,
        _HIGH_CONTRAST,
    )
}

DEFAULT_THEME_ID = _DARK_PLUS.id


def list_themes() -> list[Theme]:
    """Return every built-in theme, in a stable display order."""

    return list(THEMES.values())


def get_theme(theme_id: str) -> Theme:
    """Return a theme by id, falling back to the default if unknown."""

    return THEMES.get(theme_id, THEMES[DEFAULT_THEME_ID])


def resolve_system_theme() -> Theme:
    """Best-effort detection of the OS light/dark preference.

    Falls back to Dark+ if Qt cannot report a color scheme (older Qt
    versions, or platforms without a system preference).
    """

    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication

        style_hints = QGuiApplication.styleHints()
        scheme = style_hints.colorScheme()

        if scheme == Qt.ColorScheme.Light:
            return _LIGHT_PLUS

        if scheme == Qt.ColorScheme.Dark:
            return _DARK_PLUS

    except Exception:  # noqa: BLE001 - best-effort platform detection
        pass

    return THEMES[DEFAULT_THEME_ID]
