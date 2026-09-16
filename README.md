# Notify — JSON Payload Viewer

A desktop app (PySide6/Qt) to paste a JSON payload and explore it as a
filterable key browser, an interactive tree, a plain-text hierarchy
outline, and a jsoncrack.com-style node-link graph — all in one
maximized window titled **Notify**.

## Project layout

```
notify_app/
├── main.py                  # entry point — launches Notify maximized
├── json_utils.py             # parse_json, extract_unique_keys, find_values_by_key, json_stats
├── ui/
│   └── main_window.py         # MainWindow: control bar, filter panel, split editor/viewer
├── widgets/
│   ├── tree_view.py            # QTreeWidget builder (Tree View tab)
│   ├── hierarchy_view.py       # indented text outline (Hierarchy View tab)
│   └── graph_view.py           # jsoncrack-style HTML graph via pyvis (Graph View tab)
├── sample.json                # example payload to try the app with
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`PySide6` bundles Qt's WebEngine module on most platforms, which is
what renders the interactive graph in-app. If your environment doesn't
have it, the app still works — the Graph View tab shows an **"Open
Graph in Browser"** button instead of an embedded view.

## Run

```bash
python main.py
```

The window opens **maximized**, titled **Notify**, with your OS's
normal minimize / maximize-restore / close buttons in the title bar
(these come for free from Qt — no extra code needed for them).

## Layout, top to bottom

1. **Control bar** (Notepad++-style strip):
   - `Filter by key:` dropdown — auto-populated with every unique key
     found anywhere in the loaded payload (however deeply nested).
   - `Clear Filter` — resets the dropdown and empties the results panel.
   - `▶ Load / Parse JSON` — parses whatever's in the editor pane below.

2. **Filter results panel** — appears right under the control bar.
   When you pick a key, this shows **every occurrence** of that key in
   the payload, each with a JSONPath (e.g.
   `$.production_lines[0].machines[1].status`) so you know exactly
   where it came from.

3. **Split view** (vertical divider — drag to resize):
   - **Left — JSON Editor**: paste your payload here.
   - **Right — Viewer**, three tabs:
     - 🌳 **Tree View** — expandable/collapsible QTreeWidget, Key/Value columns.
     - 📂 **Hierarchy View** — plain-text Unicode-box-drawing outline (`├──`, `└──`), easy to scan or copy out.
     - 🕸️ **Graph View (jsoncrack-style)** — physics-based node-link diagram: purple boxes = objects, blue boxes = arrays, green ellipses = leaf values. Drag nodes, scroll to zoom.

## Try it

1. Run `python main.py`.
2. Paste the contents of `sample.json` into the left editor pane (or
   open it and copy/paste).
3. Click **▶ Load / Parse JSON**.
4. Pick `status` from the **Filter by key** dropdown — you'll see all
   5 occurrences across the payload, each with its path.
5. Click **Clear Filter** to go back.
6. Switch between the Tree / Hierarchy / Graph tabs on the right to
   see the same payload three different ways.

## Troubleshooting

- **Graph tab shows a note instead of a live graph** — your PySide6
  install doesn't include WebEngine. Run:
  ```bash
  pip install PySide6-WebEngine
  ```
  Until then, use the **Open Graph in Browser** button — it writes the
  same interactive graph to a temp `.html` file and opens it in your
  default browser.

- **"Invalid JSON" dialog on Load** — the error message includes the
  line/column where parsing failed; fix that spot in the editor and
  click Load again.

## Extending it

- **Search by value, not just key**: add a `find_by_value()` sibling
  to `find_values_by_key()` in `json_utils.py`, same recursive-walk
  pattern.
- **Syntax highlighting in the editor**: swap `QPlainTextEdit` for a
  `QPlainTextEdit` + a `QSyntaxHighlighter` subclass that colors JSON
  tokens (keys, strings, numbers, booleans).
- **Save/Export**: add a toolbar button that writes
  `self.editor.toPlainText()` to a `.json` file, or exports the graph
  HTML permanently via `net.write_html("graph.html")` in
  `graph_view.py`.
