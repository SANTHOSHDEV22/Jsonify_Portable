"""Interactive graph visualization for JSON payloads."""

from __future__ import annotations

import json
from html import escape

from jsonify.core.models import JSONValue


_MAX_LABEL_LENGTH = 60


def build_graph_html(
    data: JSONValue,
) -> str:
    """
    Build an interactive HTML graph for a JSON payload.

    The generated HTML uses vis-network and can be displayed by
    QWebEngineView or opened in an external browser.

    Args:
        data:
            Parsed JSON payload.

    Returns:
        Complete HTML document.
    """
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []

    next_id = 0

    def add_node(
        value: JSONValue,
        label: str,
        parent_id: int | None = None,
    ) -> int:
        nonlocal next_id

        node_id = next_id
        next_id += 1

        node_type = _type_name(value)

        display_label = _node_label(
            label=label,
            value=value,
        )

        nodes.append(
            {
                "id": node_id,
                "label": display_label,
                "title": _tooltip(
                    label=label,
                    value=value,
                ),
                "group": node_type,
                "shape": _node_shape(value),
            }
        )

        if parent_id is not None:
            edges.append(
                {
                    "from": parent_id,
                    "to": node_id,
                }
            )

        if isinstance(value, dict):
            for key, child_value in value.items():
                add_node(
                    value=child_value,
                    label=str(key),
                    parent_id=node_id,
                )

        elif isinstance(value, list):
            for index, child_value in enumerate(value):
                add_node(
                    value=child_value,
                    label=f"[{index}]",
                    parent_id=node_id,
                )

        return node_id

    add_node(
        value=data,
        label="$",
    )

    nodes_json = json.dumps(
        nodes,
        ensure_ascii=False,
    )

    edges_json = json.dumps(
        edges,
        ensure_ascii=False,
    )

    return _build_html_document(
        nodes_json=nodes_json,
        edges_json=edges_json,
    )


def _node_label(
    label: str,
    value: JSONValue,
) -> str:
    """Create a concise graph-node label."""

    if isinstance(value, dict):
        return (
            f"{label}\n"
            f"{{{len(value)} keys}}"
        )

    if isinstance(value, list):
        return (
            f"{label}\n"
            f"[{len(value)} items]"
        )

    formatted_value = _primitive_text(
        value
    )

    if len(formatted_value) > _MAX_LABEL_LENGTH:
        formatted_value = (
            formatted_value[
                : _MAX_LABEL_LENGTH - 3
            ]
            + "..."
        )

    return (
        f"{label}\n"
        f"{formatted_value}"
    )


def _tooltip(
    label: str,
    value: JSONValue,
) -> str:
    """Create safe HTML tooltip content."""

    value_type = _type_name(
        value
    )

    if isinstance(
        value,
        (dict, list),
    ):
        value_text = json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )

    else:
        value_text = _primitive_text(
            value
        )

    return (
        "<div style='white-space: pre-wrap;'>"
        f"<strong>{escape(label)}</strong>"
        "<br>"
        f"Type: {escape(value_type)}"
        "<br><br>"
        f"{escape(value_text)}"
        "</div>"
    )


def _primitive_text(
    value: JSONValue,
) -> str:
    """Convert a primitive JSON value to readable text."""

    if value is None:
        return "null"

    if isinstance(value, bool):
        return (
            "true"
            if value
            else "false"
        )

    if isinstance(value, str):
        return value

    return str(value)


def _type_name(
    value: JSONValue,
) -> str:
    """Return a JSON-friendly type name."""

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, dict):
        return "object"

    if isinstance(value, list):
        return "array"

    if isinstance(value, str):
        return "string"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "number"

    return type(value).__name__


def _node_shape(
    value: JSONValue,
) -> str:
    """Return graph shape according to JSON value type."""

    if isinstance(value, dict):
        return "box"

    if isinstance(value, list):
        return "ellipse"

    return "dot"


def _build_html_document(
    nodes_json: str,
    edges_json: str,
) -> str:
    """Build the complete graph HTML document."""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Jsonify Graph</title>

    <script
        src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js">
    </script>

    <style>
        html,
        body {{
            width: 100%;
            height: 100%;
            margin: 0;
            overflow: hidden;
            background: #1e1e1e;
        }}

        #graph {{
            width: 100%;
            height: 100vh;
        }}
    </style>
</head>

<body>

<div id="graph"></div>

<script>
    const nodes = new vis.DataSet(
        {nodes_json}
    );

    const edges = new vis.DataSet(
        {edges_json}
    );

    const container =
        document.getElementById("graph");

    const data = {{
        nodes: nodes,
        edges: edges
    }};

    const options = {{
        autoResize: true,

        interaction: {{
            hover: true,
            navigationButtons: true,
            keyboard: true
        }},

        physics: {{
            enabled: true,

            stabilization: {{
                iterations: 250
            }},

            barnesHut: {{
                gravitationalConstant: -4500,
                springLength: 150,
                springConstant: 0.04
            }}
        }},

        layout: {{
            improvedLayout: true
        }},

        nodes: {{
            font: {{
                color: "#d4d4d4",
                face: "Consolas",
                size: 13
            }},

            borderWidth: 1,

            margin: 10
        }},

        edges: {{
            arrows: {{
                to: {{
                    enabled: true,
                    scaleFactor: 0.5
                }}
            }},

            smooth: {{
                enabled: true,
                type: "dynamic"
            }}
        }},

        groups: {{
            object: {{
                shape: "box"
            }},

            array: {{
                shape: "ellipse"
            }},

            string: {{
                shape: "dot"
            }},

            integer: {{
                shape: "dot"
            }},

            number: {{
                shape: "dot"
            }},

            boolean: {{
                shape: "dot"
            }},

            null: {{
                shape: "dot"
            }}
        }}
    }};

    const network = new vis.Network(
        container,
        data,
        options
    );

    network.once(
        "stabilizationIterationsDone",
        function () {{
            network.fit({{
                animation: true
            }});

            network.setOptions({{
                physics: false
            }});
        }}
    );
</script>

</body>
</html>
"""