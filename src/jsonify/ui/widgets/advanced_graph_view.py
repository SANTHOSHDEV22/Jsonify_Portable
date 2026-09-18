"""Advanced interactive JSON graph."""

from __future__ import annotations

import json
import os
import tempfile
import webbrowser
from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import (
    QWebEngineView,
)

from jsonify.core.models import JSONValue
from jsonify.services.advanced_graph_service import (
    AdvancedGraphService,
    GraphData,
)


class AdvancedGraphView(QWidget):
    """Interactive advanced JSON graph."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._service = AdvancedGraphService()

        self._payload: JSONValue | None = None
        self._graph_data: GraphData | None = None
        self._last_html: str | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build graph UI."""

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        self._search = QLineEdit()

        self._search.setPlaceholderText(
            "Search node, value or JSON path..."
        )

        search_button = QPushButton(
            "Search"
        )

        search_button.clicked.connect(
            self._search_graph
        )

        reset_button = QPushButton(
            "Reset"
        )

        reset_button.clicked.connect(
            self._reset_graph
        )

        fit_button = QPushButton(
            "Fit"
        )

        fit_button.clicked.connect(
            self._fit_graph
        )

        expand_button = QPushButton(
            "Expand All"
        )

        expand_button.clicked.connect(
            self._expand_all
        )

        collapse_button = QPushButton(
            "Collapse All"
        )

        collapse_button.clicked.connect(
            self._collapse_all
        )

        fullscreen_button = QPushButton(
            "Fullscreen"
        )

        fullscreen_button.clicked.connect(
            self._toggle_fullscreen
        )

        # QWebEngineView depends on Chromium's GPU/compositor stack,
        # which can fail to initialize on some machines (VMs, locked-
        # down or unsupported GPU drivers) even when the graph HTML
        # itself is perfectly valid — no combination of Chromium flags
        # fixes this on every machine, and a wrong combination can even
        # make Chromium refuse to start at all. So this button is
        # always available as a guaranteed-working fallback: it writes
        # the exact same graph HTML to a temp file and opens it in the
        # system's default browser, which doesn't depend on
        # QtWebEngine at all.
        open_browser_button = QPushButton(
            "Open in Browser"
        )

        open_browser_button.clicked.connect(
            self._open_graph_in_browser
        )

        self._labels_checkbox = QCheckBox(
            "Labels"
        )

        self._labels_checkbox.setChecked(
            True
        )

        self._labels_checkbox.toggled.connect(
            self._toggle_labels
        )

        toolbar.addWidget(
            self._search,
            1,
        )

        toolbar.addWidget(
            search_button
        )

        toolbar.addWidget(
            reset_button
        )

        toolbar.addWidget(
            fit_button
        )

        toolbar.addWidget(
            expand_button
        )

        toolbar.addWidget(
            collapse_button
        )

        toolbar.addWidget(
            self._labels_checkbox
        )

        toolbar.addWidget(
            fullscreen_button
        )

        toolbar.addWidget(
            open_browser_button
        )

        layout.addLayout(
            toolbar
        )

        depth_layout = QHBoxLayout()

        depth_layout.addWidget(
            QLabel("Depth:")
        )

        self._depth_slider = QSlider(
            Qt.Orientation.Horizontal
        )

        self._depth_slider.setMinimum(1)
        self._depth_slider.setMaximum(10)
        self._depth_slider.setValue(10)

        self._depth_value = QLabel(
            "10"
        )

        self._depth_slider.valueChanged.connect(
            self._depth_changed
        )

        depth_layout.addWidget(
            self._depth_slider,
            1,
        )

        depth_layout.addWidget(
            self._depth_value
        )

        layout.addLayout(
            depth_layout
        )

        self._stats = QLabel(
            "Load JSON to display graph."
        )

        layout.addWidget(
            self._stats
        )

        self._web_view = QWebEngineView()

        layout.addWidget(
            self._web_view,
            1,
        )

        self._search.returnPressed.connect(
            self._search_graph
        )

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Load JSON into the graph."""

        self._payload = payload

        self._graph_data = (
            self._service.build(
                payload
            )
        )

        stats = (
            self._graph_data.statistics
        )

        maximum_depth = max(
            stats.max_depth,
            1,
        )

        self._depth_slider.setMaximum(
            maximum_depth
        )

        self._depth_slider.setValue(
            maximum_depth
        )

        truncated_text = (
            " | Limited to first "
            f"{self._service.node_limit:,} nodes"
            if self._graph_data.truncated
            else ""
        )

        self._stats.setText(
            (
                f"Nodes: {stats.total_nodes:,} | "
                f"Objects: {stats.object_nodes:,} | "
                f"Arrays: {stats.array_nodes:,} | "
                f"Values: {stats.primitive_nodes:,} | "
                f"Depth: {stats.max_depth}"
                f"{truncated_text}"
            )
        )

        self._render_graph()

    def clear_payload(self) -> None:
        """Clear graph."""

        self._payload = None
        self._graph_data = None
        self._last_html = None

        self._web_view.setHtml("")

        self._stats.setText(
            "Load JSON to display graph."
        )

    def _open_graph_in_browser(self) -> None:
        """Open the current graph in the system's default browser.

        Reuses one fixed filename in the OS temp folder across every
        click/session, instead of creating a fresh randomly-named temp
        file each time — the browser just reloads this one file with
        whatever the current graph is, so nothing accumulates on disk
        no matter how many times this button is clicked.
        """

        if not self._last_html:
            QMessageBox.information(
                self,
                "No graph yet",
                "Load a JSON payload first.",
            )

            return

        path = os.path.join(
            tempfile.gettempdir(),
            "jsonify_graph_view.html",
        )

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self._last_html)

        webbrowser.open(f"file://{path}")

    def _render_graph(self) -> None:
        """Render D3 graph."""

        if self._graph_data is None:
            return

        d3_path = (
            files("jsonify.resources")
            .joinpath("d3.min.js")
        )

        d3_source = d3_path.read_text(
            encoding="utf-8"
        )

        nodes = [
            {
                "id": node.node_id,
                "parentId": node.parent_id,
                "name": node.name,
                "path": node.path,
                "type": node.node_type,
                "value": node.value,
                "depth": node.depth,
                "hasChildren": node.has_children,
            }
            for node in self._graph_data.nodes
        ]

        graph_json = json.dumps(
            nodes,
            ensure_ascii=False,
        )

        html = self._build_html(
            d3_source,
            graph_json,
        )

        self._last_html = html

        self._web_view.setHtml(
            html
        )

    @staticmethod
    def _build_html(
        d3_source: str,
        graph_json: str,
    ) -> str:
        """Build self-contained graph HTML."""

        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>
html, body {{
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family: Arial, sans-serif;
}}

#graph {{
    width: 100%;
    height: 100%;
}}

.link {{
    stroke: #999;
    stroke-opacity: 0.45;
}}

.node circle {{
    stroke: #fff;
    stroke-width: 1.5px;
    cursor: pointer;
}}

.node text {{
    font-size: 11px;
    pointer-events: none;
}}

.node.search-match circle {{
    stroke: #ff9800;
    stroke-width: 5px;
}}

.node.selected circle {{
    stroke: #e91e63;
    stroke-width: 5px;
}}

.tooltip {{
    position: absolute;
    display: none;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 8px 10px;
    border-radius: 5px;
    font-size: 12px;
    max-width: 450px;
    pointer-events: none;
}}
</style>

<script>
{d3_source}
</script>
</head>

<body>

<svg id="graph"></svg>

<div
    id="tooltip"
    class="tooltip">
</div>

<script>

const rawNodes = {graph_json};

const nodeById = new Map(
    rawNodes.map(d => [d.id, d])
);

rawNodes.forEach(d => {{
    d.children = [];
    d._children = [];
}});

let rootData = null;

rawNodes.forEach(d => {{
    if (d.parentId === null) {{
        rootData = d;
        return;
    }}

    const parent = nodeById.get(
        d.parentId
    );

    if (parent) {{
        parent.children.push(d);
    }}
}});

const width =
    document.documentElement.clientWidth;

const height =
    document.documentElement.clientHeight;

const svg = d3.select("#graph")
    .attr("viewBox",
        [0, 0, width, height]);

const container =
    svg.append("g");

const linkLayer =
    container.append("g");

const nodeLayer =
    container.append("g");

const zoom = d3.zoom()
    .scaleExtent([0.05, 5])
    .on("zoom", event => {{
        container.attr(
            "transform",
            event.transform
        );
    }});

svg.call(zoom);

const tooltip =
    d3.select("#tooltip");

let labelsVisible = true;
let depthLimit = 999;

function nodeColor(d) {{
    switch (d.data.type) {{
        case "object":
            return "#1976d2";

        case "array":
            return "#7b1fa2";

        case "string":
            return "#388e3c";

        case "integer":
        case "number":
            return "#f57c00";

        case "boolean":
            return "#0097a7";

        case "null":
            return "#757575";

        default:
            return "#607d8b";
    }}
}}

function visibleChildren(node) {{
    if (node.depth >= depthLimit) {{
        return [];
    }}

    return node.children || [];
}}

function update() {{

    if (!rootData) {{
        return;
    }}

    const root =
        d3.hierarchy(
            rootData,
            visibleChildren
        );

    const tree =
        d3.tree()
            .nodeSize([32, 190]);

    tree(root);

    const nodes =
        root.descendants();

    const links =
        root.links();

    const link =
        linkLayer
            .selectAll("path")
            .data(
                links,
                d => d.target.data.id
            );

    link.exit().remove();

    link.enter()
        .append("path")
        .attr("class", "link")
        .merge(link)
        .attr(
            "fill",
            "none"
        )
        .attr(
            "stroke-width",
            1.2
        )
        .attr(
            "d",
            d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x)
        );

    const node =
        nodeLayer
            .selectAll("g.node")
            .data(
                nodes,
                d => d.data.id
            );

    node.exit().remove();

    const enter =
        node.enter()
            .append("g")
            .attr(
                "class",
                "node"
            );

    enter.append("circle")
        .attr("r", 7);

    enter.append("text")
        .attr("x", 12)
        .attr("dy", "0.35em");

    const merged =
        enter.merge(node);

    merged.attr(
        "transform",
        d =>
            `translate(${{d.y}},${{d.x}})`
    );

    merged.select("circle")
        .attr(
            "fill",
            d => nodeColor(d)
        );

    merged.select("text")
        .text(
            d => d.data.name
        )
        .style(
            "display",
            labelsVisible
                ? null
                : "none"
        );

    merged.on(
        "click",
        (event, d) => {{
            event.stopPropagation();

            const data = d.data;

            if (
                data.children
                && data.children.length
            ) {{
                data._children =
                    data.children;

                data.children = [];
            }}
            else if (
                data._children
                && data._children.length
            ) {{
                data.children =
                    data._children;

                data._children = [];
            }}

            update();
        }}
    );

    merged.on(
        "mouseover",
        (event, d) => {{

            tooltip
                .style(
                    "display",
                    "block"
                )
                .html(
                    `<b>${{escapeHtml(
                        d.data.path
                    )}}</b><br>` +
                    `Type: ${{escapeHtml(
                        d.data.type
                    )}}<br>` +
                    `Value: ${{escapeHtml(
                        d.data.value
                    )}}`
                );
        }}
    );

    merged.on(
        "mousemove",
        event => {{
            tooltip
                .style(
                    "left",
                    (event.pageX + 12)
                    + "px"
                )
                .style(
                    "top",
                    (event.pageY + 12)
                    + "px"
                );
        }}
    );

    merged.on(
        "mouseout",
        () => {{
            tooltip.style(
                "display",
                "none"
            );
        }}
    );
}}

function escapeHtml(value) {{
    const div =
        document.createElement("div");

    div.textContent =
        String(value);

    return div.innerHTML;
}}

function fitGraph() {{

    const bounds =
        container.node()
            .getBBox();

    if (
        !bounds.width
        || !bounds.height
    ) {{
        return;
    }}

    const fullWidth =
        document.documentElement.clientWidth;

    const fullHeight =
        document.documentElement.clientHeight;

    const scale =
        Math.min(
            0.95,
            Math.min(
                fullWidth
                    / (bounds.width + 100),
                fullHeight
                    / (bounds.height + 100)
            )
        );

    const x =
        (
            fullWidth
            - bounds.width * scale
        ) / 2
        - bounds.x * scale;

    const y =
        (
            fullHeight
            - bounds.height * scale
        ) / 2
        - bounds.y * scale;

    svg.transition()
        .duration(300)
        .call(
            zoom.transform,
            d3.zoomIdentity
                .translate(x, y)
                .scale(scale)
        );
}}

function resetGraph() {{

    expandAll();

    depthLimit = 999;

    update();

    svg.transition()
        .duration(250)
        .call(
            zoom.transform,
            d3.zoomIdentity
                .translate(60, height / 2)
                .scale(0.85)
        );
}}

function searchGraph(query) {{

    const normalized =
        String(query || "")
            .trim()
            .toLowerCase();

    nodeLayer
        .selectAll("g.node")
        .classed(
            "search-match",
            false
        );

    if (!normalized) {{
        return;
    }}

    nodeLayer
        .selectAll("g.node")
        .classed(
            "search-match",
            d => {{
                const data = d.data;

                return (
                    String(data.name)
                        .toLowerCase()
                        .includes(normalized)
                    ||
                    String(data.path)
                        .toLowerCase()
                        .includes(normalized)
                    ||
                    String(data.value)
                        .toLowerCase()
                        .includes(normalized)
                );
            }}
        );
}}

function collapseAll() {{

    rawNodes.forEach(d => {{
        if (
            d.children
            && d.children.length
        ) {{
            d._children =
                d.children;

            d.children = [];
        }}
    );

    if (
        rootData
        && rootData._children.length
    ) {{
        rootData.children =
            rootData._children;

        rootData._children = [];
    }}

    if (rootData) {{
        rootData.children.forEach(
            child => {{
                if (
                    child.children
                    && child.children.length
                ) {{
                    child._children =
                        child.children;

                    child.children = [];
                }}
            }}
        );
    }}

    update();
}}

function expandAll() {{

    rawNodes.forEach(d => {{
        if (
            d._children
            && d._children.length
        ) {{
            d.children =
                d._children;

            d._children = [];
        }}
    );

    update();
}}

function setDepth(depth) {{
    depthLimit =
        Number(depth);

    update();
}}

function setLabels(visible) {{
    labelsVisible =
        Boolean(visible);

    nodeLayer
        .selectAll("text")
        .style(
            "display",
            labelsVisible
                ? null
                : "none"
        );
}}

update();

setTimeout(
    () => {{
        svg.call(
            zoom.transform,
            d3.zoomIdentity
                .translate(60, height / 2)
                .scale(0.85)
        );
    }},
    100
);

</script>

</body>
</html>
"""

    def _run_js(
        self,
        script: str,
    ) -> None:
        """Execute JavaScript in graph."""

        self._web_view.page().runJavaScript(
            script
        )

    def _search_graph(self) -> None:
        """Highlight matching graph nodes."""

        query = json.dumps(
            self._search.text()
        )

        self._run_js(
            f"searchGraph({query});"
        )

    def _reset_graph(self) -> None:
        """Reset graph state."""

        self._search.clear()

        self._depth_slider.setValue(
            self._depth_slider.maximum()
        )

        self._labels_checkbox.setChecked(
            True
        )

        self._run_js(
            "resetGraph();"
        )

    def _fit_graph(self) -> None:
        """Fit graph to viewport."""

        self._run_js(
            "fitGraph();"
        )

    def _expand_all(self) -> None:
        """Expand graph nodes."""

        self._run_js(
            "expandAll();"
        )

    def _collapse_all(self) -> None:
        """Collapse graph nodes."""

        self._run_js(
            "collapseAll();"
        )

    def _depth_changed(
        self,
        depth: int,
    ) -> None:
        """Change visible graph depth."""

        self._depth_value.setText(
            str(depth)
        )

        self._run_js(
            f"setDepth({depth});"
        )

    def _toggle_labels(
        self,
        visible: bool,
    ) -> None:
        """Show or hide graph labels."""

        javascript_value = (
            "true"
            if visible
            else "false"
        )

        self._run_js(
            f"setLabels({javascript_value});"
        )

    def _toggle_fullscreen(self) -> None:
        """Toggle graph fullscreen mode."""

        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()