# Jsonify

Jsonify is a desktop application for viewing, exploring, filtering, and visualizing JSON payloads.

The application is built with Python and PySide6 and provides multiple ways to inspect complex and deeply nested JSON data, including tree, hierarchy, filtered, and interactive graph views.

---

## Features

### JSON Parsing

- Parse standard JSON documents.
- Parse nested JSON objects and arrays.
- Support multiple consecutive JSON documents.
- Display useful validation errors for invalid JSON payloads.

Example:

```json
{
  "company": "Example Company",
  "departments": [
    {
      "name": "Engineering",
      "members": [
        {
          "name": "Alice",
          "active": true
        }
      ]
    }
  ]
}
```

Jsonify also supports multiple consecutive JSON documents:

```json
{"company": "Company A"}
{"company": "Company B"}
{"company": "Company C"}
```

---

## Views

Jsonify provides four ways to inspect a loaded JSON payload.

### Normal View

Displays the JSON structure using an expandable tree.

Each entry shows:

- Key or array index
- Value
- JSON data type

This view is useful for quickly navigating nested objects and arrays.

### Hierarchy View

Displays the complete JSON structure as formatted hierarchical text.

This is useful when the relationship between nested objects needs to be inspected without manually expanding tree nodes.

### Filtered View

Allows JSON structures to be explored by selecting keys level by level.

The available keys are dynamically determined from the currently selected hierarchy path.

This makes it easier to inspect specific portions of large JSON documents.

### Graph View

Displays the JSON hierarchy as an interactive graph.

The graph is rendered using D3.js and supports:

- Zoom in
- Zoom out
- Mouse-wheel zoom
- Pan
- Reset view
- Fit entire graph
- Parent-child relationship visualization

D3.js is bundled locally with the application, allowing the graph to work without requiring an internet connection.

---

## Technology Stack

- Python
- PySide6
- Qt
- D3.js
- HTML
- CSS
- JavaScript
- pytest

---

## Project Structure

```text
Jsonify/
│
├── src/
│   └── jsonify/
│       │
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── parser.py
│       │   └── traversal.py
│       │
│       ├── resources/
│       │   ├── __init__.py
│       │   └── d3.min.js
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── graph_service.py
│       │   └── json_service.py
│       │
│       └── ui/
│           ├── __init__.py
│           ├── constants.py
│           ├── main_window.py
│           │
│           └── widgets/
│               ├── __init__.py
│               ├── graph_view.py
│               ├── hierarchy_view.py
│               └── tree_view.py
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_traversal.py
│   ├── test_json_service.py
│   └── test_graph_service.py
│
├── .gitignore
├── README.md
├── pyproject.toml
└── requirements.txt
```

---

## Architecture

Jsonify follows a layered structure that separates JSON processing, application services, user-interface logic, and static resources.

```text
┌─────────────────────────────────────┐
│              UI Layer               │
│                                     │
│  MainWindow                         │
│  Tree View                          │
│  Hierarchy View                     │
│  Filtered View                      │
│  Graph View                         │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│           Service Layer             │
│                                     │
│  JsonService                        │
│  GraphService                       │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│             Core Layer              │
│                                     │
│  Parser                             │
│  Traversal                          │
│  Models                             │
└─────────────────────────────────────┘

        Static Resources
               │
               ▼
          d3.min.js
```

### Core Layer

The `core` package contains JSON-related logic that does not depend on the graphical user interface.

#### `models.py`

Defines shared JSON type aliases used throughout the application.

#### `parser.py`

Handles JSON parsing, including support for multiple consecutive JSON documents.

#### `traversal.py`

Contains recursive JSON operations including:

- Unique-key extraction
- Key searching
- JSON path generation
- JSON statistics

### Service Layer

The `services` package provides application-level operations between the core functionality and the UI.

#### `json_service.py`

Provides high-level JSON operations used by the application.

#### `graph_service.py`

Handles generated graph HTML files, including temporary file creation and cleanup.

### UI Layer

The `ui` package contains PySide6 user-interface components.

#### `main_window.py`

Contains the main application window and coordinates interactions between the editor, services, and visualization components.

#### `widgets/tree_view.py`

Creates and populates the expandable JSON tree.

#### `widgets/hierarchy_view.py`

Generates hierarchy and filtered hierarchy representations.

#### `widgets/graph_view.py`

Transforms JSON structures into graph data and generates the interactive D3.js visualization.

### Resources

Static resources required by the application are stored separately from Python source code.

```text
resources/
├── __init__.py
└── d3.min.js
```

The bundled D3.js resource allows graph visualization without downloading D3 at runtime.

---

## Requirements

Python 3.12 or later is recommended.

The primary application dependency is:

```text
PySide6
```

Development dependencies include:

```text
pytest
pytest-cov
ruff
mypy
```

---

## Installation

Clone the repository:

```powershell
git clone <repository-url>
```

Move into the project directory:

```powershell
cd Jsonify
```

Create a virtual environment:

```powershell
python -m venv venv
```

Activate the virtual environment in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install Jsonify in editable mode:

```powershell
python -m pip install -e .
```

For development, install the optional development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

---

## Running the Application

After installation, start Jsonify with:

```powershell
python -m jsonify
```

If the project script entry point is installed, it can also be started with:

```powershell
jsonify
```

---

## Using Jsonify

Start the application:

```powershell
python -m jsonify
```

Paste a JSON payload into the **JSON Editor**.

Click:

```text
Load JSON
```

After the JSON has been parsed successfully, use the available viewer tabs:

```text
Normal View
Hierarchy View
Filtered View
Graph View
```

---

## Graph Controls

The Graph View provides several navigation controls.

### Zoom In

```text
+
```

Increases the graph zoom level.

### Zoom Out

```text
-
```

Decreases the graph zoom level.

### Reset

```text
Reset
```

Returns the graph to its default readable zoom and starting position.

### Fit

```text
Fit
```

Fits the entire graph into the available viewport.

For large JSON documents, the Fit operation may intentionally display nodes at a smaller scale so that the complete hierarchy is visible.

The graph can also be panned and zoomed interactively.

---

## Running Tests

Run the complete test suite:

```powershell
python -m pytest
```

Run tests with detailed output:

```powershell
python -m pytest -v
```

Run tests with coverage:

```powershell
python -m pytest --cov=jsonify --cov-report=term-missing
```

Generate an HTML coverage report:

```powershell
python -m pytest --cov=jsonify --cov-report=html
```

The generated report will be available under:

```text
htmlcov/
```

---

## Code Quality

### Ruff

Run the Ruff linter:

```powershell
python -m ruff check .
```

Automatically fix supported issues:

```powershell
python -m ruff check . --fix
```

Check formatting:

```powershell
python -m ruff format --check .
```

Format the project:

```powershell
python -m ruff format .
```

### Mypy

Run static type checking:

```powershell
python -m mypy src/jsonify
```

---

## Development Workflow

A typical development workflow is:

```powershell
git pull

.\venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"

python -m pytest

python -m ruff check .

python -m jsonify
```

Before creating a pull request, verify that:

- The application starts successfully.
- JSON loading works.
- Normal View works.
- Hierarchy View works.
- Filtered View works.
- Graph View works.
- Tests pass.
- Ruff reports no unexpected issues.

---

## Example JSON

The following payload can be used for a quick application test:

```json
{
  "company": "Example Robotics",
  "departments": [
    {
      "name": "Engineering",
      "teams": [
        {
          "name": "Firmware",
          "members": [
            {
              "name": "Alice",
              "tasks": [
                {
                  "id": "T-1",
                  "title": "Bootloader update",
                  "status": "done",
                  "subtasks": [
                    {
                      "id": "ST-1",
                      "description": "Update flash driver",
                      "done": true
                    },
                    {
                      "id": "ST-2",
                      "description": "Run regression tests",
                      "done": true
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Development Principles

The project is structured around several principles:

**Separation of concerns** — parsing, business logic, visualization, and UI code are kept in separate modules.

**Testability** — core functionality and services are designed so they can be tested without launching the desktop interface.

**Maintainability** — large features are separated into focused modules rather than being placed in a single application file.

**Offline graph support** — D3.js is bundled as an application resource rather than fetched from the internet every time the graph is opened.

**Package-based execution** — the application uses the `src` package layout and can be launched using `python -m jsonify`.

---

## Troubleshooting

### `No module named jsonify`

Install the project in editable mode:

```powershell
python -m pip install -e .
```

Then verify the package:

```powershell
python -c "import jsonify; print(jsonify.__file__)"
```

### Graph View does not display

Verify that the D3.js resource exists:

```text
src/jsonify/resources/d3.min.js
```

Test resource loading:

```powershell
python -c "from importlib.resources import files; p=files('jsonify.resources').joinpath('d3.min.js'); print(len(p.read_text(encoding='utf-8')))"
```

If a positive file size is displayed, the D3 resource is being found successfully.

### Tests cannot import `jsonify`

Install the package and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Then run:

```powershell
python -m pytest
```

---

## License

No license has been specified for this project yet.