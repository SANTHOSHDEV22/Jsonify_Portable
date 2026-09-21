# Jsonify

A free, offline desktop toolkit for working with JSON — view it, edit it, query it, diff it, validate it, convert it, mask it, and call APIs that return it. Built with Python and PySide6, with a VS Code–style interface and eight built-in themes.

Everything runs on your machine. The only network traffic is what you ask for (the API client, and the optional update check).

- [Quick start](#quick-start)
- [Running: dev vs. production](#running-dev-vs-production)
- [Features](#features)
- [Command-line interface](#command-line-interface)
- [jq-lite reference](#jq-lite-reference)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Themes](#themes)
- [Portable mode and data locations](#portable-mode-and-data-locations)
- [Plugins](#plugins)
- [Project structure](#project-structure)
- [Development](#development)
- [Building a release](#building-a-release)
- [Troubleshooting](#troubleshooting)

---

## Quick start

You need **Python 3.11 or newer** ([python.org](https://www.python.org/downloads/)). Then:

```powershell
git clone https://github.com/santhoshkumard15092000/Jsonify.git
cd Jsonify
run_dev.cmd
```

`run_dev.cmd` creates a virtual environment in `.\venv`, installs everything, and starts the app. The first run takes a few minutes (PySide6 is large); later runs start immediately.

On macOS / Linux use `./run_dev.sh` instead.

To open a file straight away: `run_dev.cmd path\to\file.json`.

---

## Running: dev vs. production

| | **Development** | **Production** |
|---|---|---|
| What runs | The Python source in `src/` (editable install) | The packaged app in `dist\Jsonify\` |
| Needs Python | Yes | No (the build bundles it) |
| Start it | `run_dev.cmd` | `run_prod.cmd` |
| Build it | — | `build_prod.cmd` |
| Best for | Changing code, running tests | Sharing with people, installers, portable use |

### Development

```powershell
run_dev.cmd              # start the app
run_dev.cmd file.json    # start the app and open a file
run_dev.cmd test         # run the test suite  (extra pytest args are passed through)
run_dev.cmd check        # ruff + formatting + mypy + tests  (what CI should run)
run_dev.cmd cli format a.json   # use the command-line interface
```

Prefer to do it by hand?

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"      # or: pip install -r requirements-dev.txt
python -m jsonify
```

### Production

```powershell
build_prod.cmd                 # -> dist\Jsonify\Jsonify.exe   (PyInstaller, one-folder)
build_prod.cmd --portable      # also -> dist\Jsonify-<version>-portable.zip
build_prod.cmd --installer     # also compiles installer\Jsonify.iss (needs Inno Setup 6)
build_prod.cmd --clean         # wipe build\ and dist\ first
run_prod.cmd                   # start the packaged app (builds it first if missing)
```

The build produces two executables in `dist\Jsonify\`:

- `Jsonify.exe` — the desktop app
- `jsonify-cli.exe` — the command-line interface (keeps a console window, unlike the app)

Options combine: `build_prod.cmd --clean --portable --installer`. The logic lives in [`scripts/build.py`](scripts/build.py) if you want to run it directly (`python scripts/build.py --help`).

---

## Features

The left rail of each document switches between tool groups. Every open file is its own tab, with its own set of tools.

### View and edit — **JSON** group

| Feature | Notes |
|---|---|
| **Editor** | Line numbers, syntax highlighting, live validation with the error underlined on its line, bracket matching, auto-indent, undo/redo |
| **Open / drop / paste** | Open dialog, drag & drop a file onto the editor, paste text, recent-files list |
| **Tree view** | Lazy-loaded (handles very large files), expand/collapse, right-click → copy key / value / node / JSONPath / JSON Pointer, jump to parent or root |
| **Type inspector** | Select a node to see its type, size, JSONPath and RFC 6901 pointer |
| **Hierarchy view** | Indented outline with `{n}` / `[n]` counts |
| **Filtered view** | Drill into the structure key by key |
| **Graph view** | Interactive D3 graph — zoom, pan, fit, expand/collapse; export to SVG / PNG / PDF |
| **Table view** | Arrays of objects as a sortable, filterable table |
| **Search** (`Ctrl+F`) | Keys, values or both · contains / case-sensitive / regex · next & previous · match count · jumps to the node in the tree |
| **Analyzer** | Duplicate array entries, objects with inconsistent shapes, mixed-type arrays, empty values, unusually deep nesting (plus any plugin analyzers) |
| **Notes** | Bookmark nodes and attach notes; both are saved in sessions |
| **Diagnostics** | Parse time, peak memory, in-memory size, node count, depth |
| **Format ▾** | Beautify (2 or 4 spaces), minify, normalize (sort keys) |
| **Repair** | Fixes trailing commas, single quotes, unquoted keys and unterminated brackets — shows what it will change and asks first |
| **Duplicate keys** | A warning banner appears when an object repeats a key (plain `json.loads` silently drops all but the last) |
| **JSONL / NDJSON** | `.jsonl` / `.ndjson` files open as arrays of records |
| **Statistics** | Node count, depth, and counts of strings / numbers / booleans / nulls plus byte size in the status bar |

### Query — **Filter**, **Query**, **jq** groups

- **Advanced filter** — keep only branches matching a key / value / type, preserving the surrounding hierarchy.
- **JSONPath** — run expressions, browse results, copy path / value / everything as JSON; query history.
- **jq** — a pure-Python subset of jq with history (see the [reference](#jq-lite-reference)).

### Compare — **Diff** group

- Side-by-side compare with added / removed / changed / type-changed values.
- **Match by key** — compare arrays of objects by an identity field (e.g. `id`) instead of position, so reordering isn't reported as changes.
- **Breaking changes only** — filters to removed properties and type changes (and newly *required* properties when compared with a schema).
- **Export report** — Markdown diff report.
- **API response diff** — the API client can send a response straight to either side; "Compare Environments" runs one request against two environments and sends both results here.

### Validate — **Schema** and **OpenAPI** groups

- **JSON Schema** (Draft 2020-12) — validate with errors shown by JSON path, or **generate a schema from a sample** payload.
- **OpenAPI** — validate a payload against one operation's response schema in an OpenAPI 3.x document (local `$ref`s are resolved).

### Transform — **Convert** and **Code** groups

- **Convert** — JSON ⇄ YAML, XML and CSV in both directions, with "Load into Jsonify".
- **Code generator** — typed models from a sample payload: **C#, Java, TypeScript, Python (dataclasses), Go, Kotlin**.

### Protect — **Mask** and **Export** groups

- **Sensitive-data detection** — by key name (`password`, `token`, …) *and* by value: emails, phone numbers, JWTs, API keys (AWS, OpenAI, GitHub, Slack, Google, private-key blocks, bearer tokens) and connection strings.
- **Masking** — mask selected fields, or **Auto-Mask Detected** to mask every finding by path. The original is never modified.
- **Export** — formatted JSON, masked JSON, **Safe JSON** (auto-masks detected data before writing), CSV, and graph images.

> Detection is heuristic and tuned to avoid false positives. It is a safety net, not a guarantee — review masked output before sharing it.

### API client — **API** group

- Methods: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS.
- Query-parameter table, headers, **JSON or form body**.
- **Auth**: Basic, Bearer token, API key (header or query), custom header.
- Response viewer: status, time, **size**, headers, body.
- **Environments** (Dev / Test / QA / Prod, and your own) with `{{variable}}` substitution — e.g. `{{base_url}}/users`.
- **History** and **Collections** you can re-run.
- **Import cURL** / **Copy as cURL**, and **Code…** to generate Python, JavaScript, C# or Java for the request.

### Developer tools — **Tools** group

JWT decoder (header, payload, expiry — *decoded locally, signature not verified*), Base64 encode/decode, JSON string escape/unescape, Unix ⇄ ISO timestamp converter, UUID generate/find/inspect, and hashes (MD5, SHA-1, SHA-256, SHA-512, SHA3-256, BLAKE2b).

### Workspace

- **Multiple tabs** — several documents at once; `Ctrl+Tab` cycles.
- **Sessions** — save the document plus the selected tool, JSONPath query, bookmarks and notes to a `.jsonify` file.
- **Crash recovery** — open tabs are snapshotted every 30 seconds; after an abnormal exit you're offered a restore.
- **Command palette** (`Ctrl+Shift+P`) — search every action.
- **Batch processing** — File → Batch Process… validates / formats / minifies / normalizes / masks / converts many files.
- **Themes** — see [Themes](#themes).
- **Optional update check** — off by default (Settings → *Check for Updates on Startup*, or About → *Check for Updates…*). It only *tells* you a newer release exists; it never downloads or installs anything.

---

## Command-line interface

The CLI shares its code with the app, never needs a display, and works in scripts and CI. After `pip install -e .` there is a `jsonify` command; from a source checkout use `python -m jsonify` (or `run_dev.cmd cli …`); in a production build use `jsonify-cli.exe`.

```text
jsonify                       open the desktop app
jsonify file.json             open the desktop app with a file
jsonify --portable            open the app in portable mode

jsonify format   FILE|-  [-i N] [--sort-keys] [-o OUT] [--in-place]
jsonify minify   FILE|-  [-o OUT]
jsonify validate FILE... (files, folders or globs)
jsonify diff     OLD NEW [--key ID] [--breaking] [--report OUT.md]
jsonify mask     FILE    [-o OUT]
jsonify convert  FILE (--to yaml|xml|csv | --from yaml|xml|csv) [-o OUT]
jsonify query    FILE EXPR [--jsonpath]
jsonify schema   FILE [--validate SCHEMA] [-o OUT]
jsonify codegen  FILE --lang csharp|java|typescript|python|go|kotlin [--name Root]
jsonify batch    OPERATION INPUT... [-o DIR] [-i N] [--in-place]
```

`OPERATION` for `batch`: `validate`, `format`, `minify`, `normalize`, `mask`, `yaml`, `xml`, `csv`.

Exit codes: **0** success · **1** the check found problems (invalid JSON, differences, schema errors) · **2** usage or I/O error. That makes it drop-in for CI:

```powershell
jsonify validate .\config\           # fails the build on any invalid file
jsonify diff old.json new.json --key id --breaking
jsonify batch format .\data -o .\formatted
type response.json | jsonify format -
```

---

## jq-lite reference

Jsonify's **jq** tab and `jsonify query` run a small, pure-Python subset of [jq](https://jqlang.github.io/jq/) — no `libjq` or extra install. It is **not** full jq.

| Syntax | Meaning |
|---|---|
| `.` | the whole value |
| `.a.b.c` | field access (missing → `null`) |
| `.a[0]`, `.a[-1]` | array index |
| `.a[]`, `.[]` | iterate an array's items or an object's values |
| `keys` | sorted keys of an object |
| `length` | length of an array / object / string; absolute value of a number |
| `select(.a == 1)` | keep the item if the condition holds — `==` `!=` `<` `>` `<=` `>=`, or just `select(.active)` for truthiness |
| `map(.a)` | apply a field path to each element of an array |
| `a \| b \| c` | pipe: each stage runs on every result of the previous one |

```text
.users[] | select(.active == true) | .name
.orders[] | select(.total > 100)
.items | map(.id)
```

Anything else (functions like `sort_by`, `group_by`, string interpolation, `reduce`, …) is reported as unsupported rather than guessed at.

---

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New document |
| `Ctrl+O` | Open file |
| `Ctrl+Enter` | Load JSON from the editor |
| `Ctrl+F` | Search keys / values |
| `Ctrl+Shift+P` | Command palette |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Next / previous document |
| `Ctrl+W` | Close document |
| `Ctrl+Shift+O` | Open session |
| `Ctrl+Shift+S` | Save session |
| `Ctrl+Q` | Quit |

Everything else is reachable through the command palette.

---

## Themes

Settings → **Theme**: *Follow System*, **Dark+**, **Light+**, **Monokai**, **Solarized Dark**, **Solarized Light**, **Dracula**, **Nord**, **High Contrast**. Themes restyle the whole window and the editor's syntax colors, and your choice is remembered. (The Graph view draws on its own dark canvas and isn't affected.)

---

## Portable mode and data locations

Jsonify keeps a few small files: settings, recent files, crash-recovery snapshot, API history / collections / environments, and plugins.

| Mode | Location |
|---|---|
| Normal | `~/.jsonify/` (`C:\Users\<you>\.jsonify\`) |
| **Portable** | a `data` folder next to the app |
| Override | the folder in the `JSONIFY_DATA_DIR` environment variable |

Portable mode turns on when **any** of these is true: you start with `--portable`, the `JSONIFY_PORTABLE` environment variable is set, or a file named `portable.flag` sits next to the executable.

To make a portable copy of a release: `build_prod.cmd --portable` produces `dist\Jsonify-<version>-portable.zip` — unzip it anywhere (USB stick, shared drive) and run `Jsonify.exe`; nothing is installed and nothing is written outside that folder. (About → *About* shows the current mode and data folder.)

Nothing sensitive is stored except what you type into the API client (environment variables, saved requests). Treat `api_workspace.json` accordingly.

---

## Plugins

Plugins can add **converters**, **analyzers** and **tools**. A plugin is a Python file with a `register(registry)` function. Drop it in the `plugins` folder inside the data folder (`~/.jsonify/plugins/`), or ship it as a package that exposes an entry point in the `jsonify.plugins` group.

```python
# ~/.jsonify/plugins/toml_support.py
import tomllib


def register(registry):
    registry.register_converter("TOML", to_json=lambda text: tomllib.loads(text))

    def find_empty_names(payload):
        return ["found an empty 'name'"] if isinstance(payload, dict) and payload.get("name") == "" else []

    registry.register_analyzer("Empty names", find_empty_names)
    registry.register_tool("Reverse", lambda text: text[::-1])
```

- Converters appear in the **Convert** tab's format lists (a converter may provide `to_json`, `from_json`, or both).
- Analyzers run whenever a document loads and report in the **Analyzer** tab.
- A plugin that fails to load never breaks the app — see About → *Loaded Plugins* for the list and any errors.

Plugins run with the same permissions as Jsonify, so only install ones you trust.

---

## Project structure

```text
Jsonify/
├── src/jsonify/
│   ├── __main__.py          entry point: CLI dispatch or desktop app
│   ├── cli.py               command-line interface (no Qt)
│   ├── core/                pure logic — parsing, diff, jq, schema, codegen, masking,
│   │                        converters, cURL, plugins, ...   (no Qt, no I/O framework)
│   ├── services/            app-level services — API client, batch, export, sessions,
│   │                        schema/OpenAPI, updates, local state
│   ├── ui/
│   │   ├── main_window.py   tabs, menus, themes, recovery, updates
│   │   ├── theme.py         theme registry and stylesheet template
│   │   └── widgets/         DocumentTab, editor, tree, API view, diff, tools, ...
│   └── resources/           bundled D3 and app icon (works offline)
├── tests/                   pytest suite (core, services, CLI, packaging)
├── scripts/build.py         production build (PyInstaller, portable zip, installer)
├── installer/Jsonify.iss    Inno Setup script
├── Jsonify.spec             PyInstaller configuration
├── run_dev.cmd | run_dev.sh     development launcher
├── run_prod.cmd | build_prod.cmd   production launcher / builder
├── pyproject.toml           packaging + tool configuration (source of truth)
└── requirements*.txt        pip requirement files (runtime / dev / build)
```

The layers depend downward only: `ui` → `services` → `core`. Most tests exercise `core` and `services` without a display; the CLI is a thin layer over the same code.

---

## Development

```powershell
run_dev.cmd test                       # pytest
run_dev.cmd check                      # ruff check, ruff format --check, mypy, pytest
python -m pytest --cov=jsonify --cov-report=term-missing
python -m ruff check . --fix           # lint (and auto-fix)
python -m ruff format .                # format
python -m mypy                         # types: core, services, CLI
```

- **Style** — Ruff, line length 100, double quotes.
- **Types** — mypy covers `core`, `services` and the CLI. The Qt widget layer is excluded deliberately: PySide6 method overrides trip mypy's override checks and would bury real problems in noise.
- **Dependencies** — declare them in `pyproject.toml`; `requirements.txt` mirrors the runtime list and a test fails if they drift apart. The version lives in `src/jsonify/__init__.py` (and `installer/Jsonify.iss`); a test keeps them equal.
- **Adding a feature** — put the logic in `core/` (or `services/` if it needs I/O), unit-test it, then add a thin widget in `ui/widgets/`.

---

## Building a release

1. Bump `__version__` in `src/jsonify/__init__.py`, `version` in `pyproject.toml`, and `MyAppVersion` in `installer/Jsonify.iss` (`run_dev.cmd test` fails until they agree).
2. `run_dev.cmd check`
3. `build_prod.cmd --clean --portable --installer`
4. Publish `installer-output\Jsonify-Setup-<version>.exe` and `dist\Jsonify-<version>-portable.zip` as a GitHub Release tagged `v<version>` — the in-app update check reads the latest release tag.

---

## Troubleshooting

**`python` / `py` is not recognized** — install Python 3.11+ and tick *Add python.exe to PATH*, then run `run_dev.cmd` again.

**The first `run_dev.cmd` looks stuck** — it's downloading PySide6 (~150 MB). Later runs are instant.

**`No module named jsonify`** — you're outside the virtual environment. Use `run_dev.cmd`, or `.\venv\Scripts\Activate.ps1` and `pip install -e .`.

**The Graph view is blank or export to PNG/PDF fails** — the graph uses Qt WebEngine. Make sure PySide6 installed completely (`pip install --force-reinstall PySide6`). The tab needs no internet — D3 is bundled.

**A large file feels slow** — the tree is lazy and paged, but the Hierarchy view is intentionally skipped past a safety limit. Use the tree, JSONPath or jq for huge documents. The Diagnostics tab shows where the time goes.

**The packaged app doesn't start** — run `dist\Jsonify\jsonify-cli.exe --version` to check the build itself; rebuild with `build_prod.cmd --clean`.

**Reset everything** — close Jsonify and delete the data folder (see [above](#portable-mode-and-data-locations)).

---

## License

No license has been chosen for this project, so no rights are granted beyond those the repository owner allows. Add a `LICENSE` file if you intend others to use or redistribute it.
