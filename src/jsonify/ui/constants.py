"""UI constants and styling for Jsonify."""

from jsonify import __version__

APP_NAME = "Jsonify"
APP_VERSION = __version__

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

# Styling (stylesheets, color tokens, and editor colors) now lives in
# jsonify.ui.theme as a proper multi-theme registry.
