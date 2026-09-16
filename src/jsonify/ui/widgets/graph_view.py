"""Interactive D3.js graph visualization for JSON payloads."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from jsonify.core.models import JSONValue

NODE_WIDTH = 280
NODE_HEADER_HEIGHT = 34
NODE_ROW_HEIGHT = 26
NODE_PADDING = 10

HORIZONTAL_GAP = 140
VERTICAL_GAP = 40

MAX_VALUE_LENGTH = 80

INITIAL_SCALE = 0.85
INITIAL_X = 40
INITIAL_Y = 40


def _load_d3_source() -> str:
    """Load the bundled D3.js JavaScript source."""

    resource = files("jsonify.resources").joinpath("d3.min.js")

    if not resource.is_file():
        raise FileNotFoundError("D3.js resource was not found at 'jsonify/resources/d3.min.js'.")

    return resource.read_text(encoding="utf-8")


def _type_name(value: JSONValue) -> str:
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


def _format_value(value: JSONValue) -> str:
    """Convert a primitive JSON value to display text."""

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, str):
        text = value
    else:
        text = str(value)

    if len(text) > MAX_VALUE_LENGTH:
        return text[: MAX_VALUE_LENGTH - 3] + "..."

    return text


def _summary(value: JSONValue) -> str:
    """Return a short description for a JSON value."""

    if isinstance(value, dict):
        count = len(value)
        return f"{count} key" if count == 1 else f"{count} keys"

    if isinstance(value, list):
        count = len(value)
        return f"{count} item" if count == 1 else f"{count} items"

    return _format_value(value)


def _build_graph_data(
    payload: JSONValue,
) -> dict[str, list[dict[str, Any]]]:
    """
    Convert a JSON payload into graph nodes and edges.

    Objects and arrays become graph nodes.
    Primitive values are displayed as rows inside their parent node.
    """

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    next_id = 0

    def create_node(
        value: JSONValue,
        label: str,
        parent_id: int | None = None,
    ) -> int:
        nonlocal next_id

        node_id = next_id
        next_id += 1

        rows: list[dict[str, Any]] = []

        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, (dict, list)):
                    rows.append(
                        {
                            "key": str(key),
                            "value": _summary(child),
                            "type": _type_name(child),
                            "container": True,
                        }
                    )

                else:
                    rows.append(
                        {
                            "key": str(key),
                            "value": _format_value(child),
                            "type": _type_name(child),
                            "container": False,
                        }
                    )

        elif isinstance(value, list):
            for index, child in enumerate(value):
                key = f"[{index}]"

                if isinstance(child, (dict, list)):
                    rows.append(
                        {
                            "key": key,
                            "value": _summary(child),
                            "type": _type_name(child),
                            "container": True,
                        }
                    )

                else:
                    rows.append(
                        {
                            "key": key,
                            "value": _format_value(child),
                            "type": _type_name(child),
                            "container": False,
                        }
                    )

        else:
            rows.append(
                {
                    "key": "value",
                    "value": _format_value(value),
                    "type": _type_name(value),
                    "container": False,
                }
            )

        nodes.append(
            {
                "id": node_id,
                "label": label,
                "type": _type_name(value),
                "rows": rows,
            }
        )

        if parent_id is not None:
            edges.append(
                {
                    "source": parent_id,
                    "target": node_id,
                    "label": label,
                }
            )

        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, (dict, list)):
                    create_node(
                        value=child,
                        label=str(key),
                        parent_id=node_id,
                    )

        elif isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, (dict, list)):
                    create_node(
                        value=child,
                        label=f"[{index}]",
                        parent_id=node_id,
                    )

        return node_id

    create_node(
        value=payload,
        label="$",
    )

    return {
        "nodes": nodes,
        "edges": edges,
    }


def build_graph_html(payload: JSONValue) -> str:
    """Build a complete standalone HTML document for the graph view."""

    d3_source = _load_d3_source()

    graph_data = _build_graph_data(payload)

    graph_json = json.dumps(
        graph_data,
        ensure_ascii=False,
    ).replace("</", "<\\/")

    return f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Jsonify Graph View</title>


<style>

html,
body {{
    margin: 0;
    padding: 0;

    width: 100%;
    height: 100%;

    overflow: hidden;

    background-color: #1e1e1e;
    color: #d4d4d4;

    font-family:
        Consolas,
        "Courier New",
        monospace;
}}


#graph-container {{
    position: relative;

    width: 100%;
    height: 100%;

    overflow: hidden;
}}


#graph {{
    display: block;

    width: 100%;
    height: 100%;
}}


.link {{
    fill: none;

    stroke: #666666;
    stroke-width: 1.5px;
}}


.edge-label {{
    fill: #aaaaaa;

    font-size: 11px;

    pointer-events: none;
}}


.node {{
    cursor: default;
}}


.node-background {{
    fill: #252526;

    stroke: #555555;
    stroke-width: 1px;

    rx: 6px;
    ry: 6px;
}}


.node-header {{
    fill: #333337;

    rx: 6px;
    ry: 6px;
}}


.node-title {{
    fill: #ffffff;

    font-size: 13px;
    font-weight: bold;
}}


.node-type {{
    fill: #9cdcfe;

    font-size: 10px;
}}


.row-divider {{
    stroke: #3f3f46;

    stroke-width: 1px;
}}


.row-key {{
    fill: #9cdcfe;

    font-size: 11px;
}}


.row-value {{
    fill: #ce9178;

    font-size: 11px;
}}


.row-value.container-value {{
    fill: #dcdcaa;
}}


.row-type {{
    fill: #6a9955;

    font-size: 9px;
}}


#toolbar {{
    position: absolute;

    top: 12px;
    right: 12px;

    z-index: 100;

    display: flex;

    gap: 6px;

    padding: 6px;

    background: rgba(37, 37, 38, 0.96);

    border: 1px solid #3f3f46;

    border-radius: 6px;
}}


#toolbar button {{
    min-width: 34px;
    height: 30px;

    padding: 0 9px;

    border: 1px solid #555555;

    border-radius: 4px;

    background: #333337;

    color: #ffffff;

    cursor: pointer;

    font-size: 14px;
}}


#toolbar button:hover {{
    background: #45454a;
}}


#toolbar button:active {{
    background: #007acc;
}}


#status {{
    position: absolute;

    left: 12px;
    bottom: 12px;

    z-index: 100;

    padding: 5px 9px;

    background: rgba(37, 37, 38, 0.92);

    color: #999999;

    border-radius: 4px;

    font-size: 11px;

    pointer-events: none;
}}


#empty-message {{
    display: none;

    position: absolute;

    left: 50%;
    top: 50%;

    transform: translate(-50%, -50%);

    color: #aaaaaa;

    font-size: 14px;
}}

</style>

</head>


<body>


<div id="graph-container">

    <div id="toolbar">

        <button
            id="zoom-in"
            title="Zoom in"
        >
            +
        </button>

        <button
            id="zoom-out"
            title="Zoom out"
        >
            −
        </button>

        <button
            id="zoom-reset"
            title="Reset to readable view"
        >
            Reset
        </button>

        <button
            id="zoom-fit"
            title="Fit entire graph"
        >
            Fit
        </button>

    </div>


    <div id="status"></div>


    <div id="empty-message">
        No graph data available.
    </div>


    <svg id="graph"></svg>

</div>


<script>

{d3_source}

</script>


<script>

(function () {{

    "use strict";


    const graphData =
        {graph_json};


    const NODE_WIDTH =
        {NODE_WIDTH};


    const HEADER_HEIGHT =
        {NODE_HEADER_HEIGHT};


    const ROW_HEIGHT =
        {NODE_ROW_HEIGHT};


    const NODE_PADDING =
        {NODE_PADDING};


    const HORIZONTAL_GAP =
        {HORIZONTAL_GAP};


    const VERTICAL_GAP =
        {VERTICAL_GAP};


    const INITIAL_SCALE =
        {INITIAL_SCALE};


    const INITIAL_X =
        {INITIAL_X};


    const INITIAL_Y =
        {INITIAL_Y};


    const container =
        document.getElementById(
            "graph-container"
        );


    const status =
        document.getElementById(
            "status"
        );


    const svg =
        d3.select(
            "#graph"
        );


    if (
        !graphData.nodes
        ||
        graphData.nodes.length === 0
    ) {{

        document
            .getElementById(
                "empty-message"
            )
            .style.display = "block";


        status.textContent =
            "0 nodes";


        return;
    }}


    status.textContent =
        `${{graphData.nodes.length}} nodes`;


    const rootLayer =
        svg
            .append(
                "g"
            )
            .attr(
                "class",
                "root-layer"
            );


    const linkLayer =
        rootLayer
            .append(
                "g"
            )
            .attr(
                "class",
                "links"
            );


    const labelLayer =
        rootLayer
            .append(
                "g"
            )
            .attr(
                "class",
                "edge-labels"
            );


    const nodeLayer =
        rootLayer
            .append(
                "g"
            )
            .attr(
                "class",
                "nodes"
            );


    const nodeMap =
        new Map(
            graphData.nodes.map(
                node => [
                    node.id,
                    node
                ]
            )
        );


    const childrenMap =
        new Map();


    graphData.nodes.forEach(
        node => {{

            childrenMap.set(
                node.id,
                []
            );
        }}
    );


    graphData.edges.forEach(
        edge => {{

            const children =
                childrenMap.get(
                    edge.source
                );


            if (children) {{

                children.push(
                    edge.target
                );
            }}
        }}
    );


    const incomingTargets =
        new Set(
            graphData.edges.map(
                edge =>
                    edge.target
            )
        );


    const rootNode =
        graphData.nodes.find(
            node =>
                !incomingTargets.has(
                    node.id
                )
        );


    if (!rootNode) {{

        status.textContent =
            "Unable to determine root node.";

        console.error(
            "Jsonify: Unable to determine graph root."
        );

        return;
    }}


    function nodeHeight(
        node
    ) {{

        const rows =
            Math.max(
                node.rows.length,
                1
            );


        return (
            HEADER_HEIGHT
            +
            rows * ROW_HEIGHT
            +
            NODE_PADDING
        );
    }}


    function buildHierarchy(
        nodeId
    ) {{

        const node =
            nodeMap.get(
                nodeId
            );


        const children =
            childrenMap.get(
                nodeId
            ) || [];


        return {{

            ...node,

            children:
                children.map(
                    childId =>
                        buildHierarchy(
                            childId
                        )
                )
        }};
    }}


    const hierarchyData =
        buildHierarchy(
            rootNode.id
        );


    const hierarchyRoot =
        d3.hierarchy(
            hierarchyData
        );


    hierarchyRoot.each(
        node => {{

            node.data.height =
                nodeHeight(
                    node.data
                );
        }}
    );


    /*
     * D3 tree orientation:
     *
     * node.x = vertical position
     * node.y = horizontal depth
     *
     * The first nodeSize value is intentionally 1.
     *
     * The separation function below already returns
     * the vertical spacing in pixels.
     *
     * Using NODE_WIDTH + HORIZONTAL_GAP as the first
     * value would multiply the separation distance
     * again and create an enormous graph.
     */
    const treeLayout =
        d3
            .tree()

            .nodeSize(
                [
                    1,
                    NODE_WIDTH
                    +
                    HORIZONTAL_GAP
                ]
            )

            .separation(
                (a, b) => {{

                    const aHeight =
                        a.data.height;


                    const bHeight =
                        b.data.height;


                    return (
                        (
                            aHeight
                            +
                            bHeight
                        )
                        /
                        2
                    )
                    +
                    VERTICAL_GAP;
                }}
            );


    treeLayout(
        hierarchyRoot
    );


    const descendants =
        hierarchyRoot.descendants();


    let minimumY =
        Infinity;


    descendants.forEach(
        node => {{

            const top =
                node.x
                -
                node.data.height
                /
                2;


            minimumY =
                Math.min(
                    minimumY,
                    top
                );
        }}
    );


    if (!Number.isFinite(minimumY)) {{

        minimumY =
            0;
    }}


    const LEFT_MARGIN =
        40;


    const TOP_MARGIN =
        40;


    descendants.forEach(
        node => {{

            node.graphX =
                LEFT_MARGIN
                +
                node.y;


            node.graphY =
                TOP_MARGIN
                +
                node.x
                -
                minimumY;
        }}
    );


    const nodeById =
        new Map(
            descendants.map(
                node => [
                    node.data.id,
                    node
                ]
            )
        );


    function edgePath(
        edge
    ) {{

        const source =
            nodeById.get(
                edge.source
            );


        const target =
            nodeById.get(
                edge.target
            );


        if (
            !source
            ||
            !target
        ) {{

            return "";
        }}


        const sourceX =
            source.graphX
            +
            NODE_WIDTH;


        const sourceY =
            source.graphY;


        const targetX =
            target.graphX;


        const targetY =
            target.graphY;


        const middleX =
            (
                sourceX
                +
                targetX
            )
            /
            2;


        return (
            `M ${{sourceX}} ${{sourceY}} `
            +
            `C ${{middleX}} ${{sourceY}}, `
            +
            `${{middleX}} ${{targetY}}, `
            +
            `${{targetX}} ${{targetY}}`
        );
    }}


    linkLayer

        .selectAll(
            "path"
        )

        .data(
            graphData.edges
        )

        .join(
            "path"
        )

        .attr(
            "class",
            "link"
        )

        .attr(
            "d",
            edgePath
        );


    labelLayer

        .selectAll(
            "text"
        )

        .data(
            graphData.edges
        )

        .join(
            "text"
        )

        .attr(
            "class",
            "edge-label"
        )

        .attr(
            "x",
            edge => {{

                const source =
                    nodeById.get(
                        edge.source
                    );


                const target =
                    nodeById.get(
                        edge.target
                    );


                if (
                    !source
                    ||
                    !target
                ) {{

                    return 0;
                }}


                return (
                    source.graphX
                    +
                    NODE_WIDTH
                    +
                    target.graphX
                )
                /
                2;
            }}
        )

        .attr(
            "y",
            edge => {{

                const source =
                    nodeById.get(
                        edge.source
                    );


                const target =
                    nodeById.get(
                        edge.target
                    );


                if (
                    !source
                    ||
                    !target
                ) {{

                    return 0;
                }}


                return (
                    source.graphY
                    +
                    target.graphY
                )
                /
                2
                -
                6;
            }}
        )

        .attr(
            "text-anchor",
            "middle"
        )

        .text(
            edge =>
                edge.label
        );


    const nodeGroups =
        nodeLayer

            .selectAll(
                "g.node"
            )

            .data(
                descendants
            )

            .join(
                "g"
            )

            .attr(
                "class",
                "node"
            )

            .attr(
                "transform",
                node => {{

                    const x =
                        node.graphX;


                    const y =
                        node.graphY
                        -
                        node.data.height
                        /
                        2;


                    return (
                        `translate(${{x}},${{y}})`
                    );
                }}
            );


    nodeGroups

        .append(
            "rect"
        )

        .attr(
            "class",
            "node-background"
        )

        .attr(
            "width",
            NODE_WIDTH
        )

        .attr(
            "height",
            node =>
                node.data.height
        );


    nodeGroups

        .append(
            "rect"
        )

        .attr(
            "class",
            "node-header"
        )

        .attr(
            "width",
            NODE_WIDTH
        )

        .attr(
            "height",
            HEADER_HEIGHT
        );


    nodeGroups

        .append(
            "text"
        )

        .attr(
            "class",
            "node-title"
        )

        .attr(
            "x",
            10
        )

        .attr(
            "y",
            21
        )

        .text(
            node =>
                node.data.label
        );


    nodeGroups

        .append(
            "text"
        )

        .attr(
            "class",
            "node-type"
        )

        .attr(
            "x",
            NODE_WIDTH - 10
        )

        .attr(
            "y",
            21
        )

        .attr(
            "text-anchor",
            "end"
        )

        .text(
            node =>
                node.data.type
        );


    nodeGroups.each(
        function (node) {{

            const group =
                d3.select(
                    this
                );


            const rows =
                node.data.rows;


            rows.forEach(
                (row, index) => {{

                    const rowY =
                        HEADER_HEIGHT
                        +
                        index
                        *
                        ROW_HEIGHT;


                    group

                        .append(
                            "line"
                        )

                        .attr(
                            "class",
                            "row-divider"
                        )

                        .attr(
                            "x1",
                            0
                        )

                        .attr(
                            "x2",
                            NODE_WIDTH
                        )

                        .attr(
                            "y1",
                            rowY
                        )

                        .attr(
                            "y2",
                            rowY
                        );


                    group

                        .append(
                            "text"
                        )

                        .attr(
                            "class",
                            "row-key"
                        )

                        .attr(
                            "x",
                            10
                        )

                        .attr(
                            "y",
                            rowY + 17
                        )

                        .text(
                            row.key
                        );


                    group

                        .append(
                            "text"
                        )

                        .attr(
                            "class",
                            row.container
                                ? "row-value container-value"
                                : "row-value"
                        )

                        .attr(
                            "x",
                            95
                        )

                        .attr(
                            "y",
                            rowY + 17
                        )

                        .text(
                            row.value
                        );


                    group

                        .append(
                            "text"
                        )

                        .attr(
                            "class",
                            "row-type"
                        )

                        .attr(
                            "x",
                            NODE_WIDTH - 8
                        )

                        .attr(
                            "y",
                            rowY + 17
                        )

                        .attr(
                            "text-anchor",
                            "end"
                        )

                        .text(
                            row.type
                        );
                }}
            );
        }}
    );


    const zoom =
        d3
            .zoom()

            .scaleExtent(
                [
                    0.05,
                    5
                ]
            )

            .on(
                "zoom",
                event => {{

                    rootLayer.attr(
                        "transform",
                        event.transform
                    );
                }}
            );


    svg.call(
        zoom
    );


    function initialTransform() {{

        return (
            d3
                .zoomIdentity

                .translate(
                    INITIAL_X,
                    INITIAL_Y
                )

                .scale(
                    INITIAL_SCALE
                )
        );
    }}


    function setInitialView(
        animate = false
    ) {{

        const transform =
            initialTransform();


        if (animate) {{

            svg

                .transition()

                .duration(
                    250
                )

                .call(
                    zoom.transform,
                    transform
                );

            return;
        }}


        svg.call(
            zoom.transform,
            transform
        );
    }}


    function fitGraph() {{

        const graphNode =
            rootLayer.node();


        if (!graphNode) {{

            return;
        }}


        const bounds =
            graphNode.getBBox();


        if (
            bounds.width <= 0
            ||
            bounds.height <= 0
        ) {{

            return;
        }}


        const currentWidth =
            container.clientWidth
            ||
            1200;


        const currentHeight =
            container.clientHeight
            ||
            800;


        const padding =
            60;


        const scale =
            Math.min(

                currentWidth
                /
                (
                    bounds.width
                    +
                    padding * 2
                ),

                currentHeight
                /
                (
                    bounds.height
                    +
                    padding * 2
                ),

                1.2
            );


        const safeScale =
            Math.max(
                0.05,
                scale
            );


        const translateX =
            currentWidth
            /
            2
            -
            safeScale
            *
            (
                bounds.x
                +
                bounds.width
                /
                2
            );


        const translateY =
            currentHeight
            /
            2
            -
            safeScale
            *
            (
                bounds.y
                +
                bounds.height
                /
                2
            );


        const transform =
            d3
                .zoomIdentity

                .translate(
                    translateX,
                    translateY
                )

                .scale(
                    safeScale
                );


        svg

            .transition()

            .duration(
                300
            )

            .call(
                zoom.transform,
                transform
            );
    }}


    document

        .getElementById(
            "zoom-in"
        )

        .addEventListener(
            "click",
            () => {{

                svg

                    .transition()

                    .duration(
                        200
                    )

                    .call(
                        zoom.scaleBy,
                        1.25
                    );
            }}
        );


    document

        .getElementById(
            "zoom-out"
        )

        .addEventListener(
            "click",
            () => {{

                svg

                    .transition()

                    .duration(
                        200
                    )

                    .call(
                        zoom.scaleBy,
                        0.8
                    );
            }}
        );


    document

        .getElementById(
            "zoom-reset"
        )

        .addEventListener(
            "click",
            () => {{

                setInitialView(
                    true
                );
            }}
        );


    document

        .getElementById(
            "zoom-fit"
        )

        .addEventListener(
            "click",
            () => {{

                fitGraph();
            }}
        );


    /*
     * IMPORTANT:
     *
     * Do NOT automatically call fitGraph() here.
     *
     * Large JSON documents can contain dozens or hundreds
     * of nodes. Fitting the entire hierarchy automatically
     * would make every node extremely small.
     *
     * Start at a readable zoom instead.
     */
    requestAnimationFrame(
        () => {{

            requestAnimationFrame(
                () => {{

                    setInitialView(
                        false
                    );
                }}
            );
        }}
    );


}})();

</script>


</body>

</html>
"""
