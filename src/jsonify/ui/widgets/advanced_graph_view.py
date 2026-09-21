"""Advanced interactive JSON graph."""

from __future__ import annotations

import json
import os
import tempfile
import webbrowser
from importlib.resources import files

from PySide6.QtCore import QByteArray, Qt, QUrl
from PySide6.QtGui import QImage, QPainter, QPdfWriter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWebEngineWidgets import (
    QWebEngineView,
)
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

        self._search.setPlaceholderText("Search node, value or JSON path...")

        search_button = QPushButton("Search")

        search_button.clicked.connect(self._search_graph)

        reset_button = QPushButton("Reset")

        reset_button.clicked.connect(self._reset_graph)

        fit_button = QPushButton("Fit")

        fit_button.clicked.connect(self._fit_graph)

        expand_button = QPushButton("Expand All")

        expand_button.clicked.connect(self._expand_all)

        collapse_button = QPushButton("Collapse All")

        collapse_button.clicked.connect(self._collapse_all)

        fullscreen_button = QPushButton("Fullscreen")

        fullscreen_button.clicked.connect(self._toggle_fullscreen)

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
        open_browser_button = QPushButton("Open in Browser")

        open_browser_button.clicked.connect(self._open_graph_in_browser)

        self._labels_checkbox = QCheckBox("Labels")

        self._labels_checkbox.setChecked(True)

        self._labels_checkbox.toggled.connect(self._toggle_labels)

        toolbar.addWidget(
            self._search,
            1,
        )

        toolbar.addWidget(search_button)

        toolbar.addWidget(reset_button)

        toolbar.addWidget(fit_button)

        toolbar.addWidget(expand_button)

        toolbar.addWidget(collapse_button)

        toolbar.addWidget(self._labels_checkbox)

        toolbar.addWidget(fullscreen_button)

        toolbar.addWidget(open_browser_button)

        layout.addLayout(toolbar)

        depth_layout = QHBoxLayout()

        depth_layout.addWidget(QLabel("Depth:"))

        self._depth_slider = QSlider(Qt.Orientation.Horizontal)

        self._depth_slider.setMinimum(1)
        self._depth_slider.setMaximum(10)
        self._depth_slider.setValue(10)

        self._depth_value = QLabel("10")

        self._depth_slider.valueChanged.connect(self._depth_changed)

        depth_layout.addWidget(
            self._depth_slider,
            1,
        )

        depth_layout.addWidget(self._depth_value)

        layout.addLayout(depth_layout)

        self._stats = QLabel("Load JSON to display graph.")

        layout.addWidget(self._stats)

        self._web_view = QWebEngineView()

        layout.addWidget(
            self._web_view,
            1,
        )

        self._search.returnPressed.connect(self._search_graph)

    def set_payload(
        self,
        payload: JSONValue,
    ) -> None:
        """Load JSON into the graph."""

        self._payload = payload

        self._graph_data = self._service.build(payload)

        stats = self._graph_data.statistics

        maximum_depth = max(
            stats.max_depth,
            1,
        )

        self._depth_slider.setMaximum(maximum_depth)

        self._depth_slider.setValue(maximum_depth)

        truncated_text = (
            f" | Limited to first {self._service.node_limit:,} nodes"
            if self._graph_data.truncated
            else ""
        )

        self._stats.setText(
            f"Nodes: {stats.total_nodes:,} | "
            f"Objects: {stats.object_nodes:,} | "
            f"Arrays: {stats.array_nodes:,} | "
            f"Values: {stats.primitive_nodes:,} | "
            f"Depth: {stats.max_depth}"
            f"{truncated_text}"
        )

        self._render_graph()

    def clear_payload(self) -> None:
        """Clear graph."""

        self._payload = None
        self._graph_data = None
        self._last_html = None

        self._web_view.setHtml("")

        self._stats.setText("Load JSON to display graph.")

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

        d3_path = files("jsonify.resources").joinpath("d3.min.js")

        d3_source = d3_path.read_text(encoding="utf-8")

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

        # Load the graph from a real local file instead of setHtml().
        # QtWebEngine is more reliable with a file URL for a large,
        # self-contained D3 document, and this is also the exact file
        # opened by the external-browser button.
        path = os.path.join(
            tempfile.gettempdir(),
            "jsonify_graph_view.html",
        )

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(html)

        self._web_view.setUrl(QUrl.fromLocalFile(path))

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
html, body {{ margin:0; width:100%; height:100%; overflow:hidden; background:#111315; font-family:Consolas, 'Courier New', monospace; }}
#graph {{ width:100%; height:100%; display:block; background-color:#111315; background-image:linear-gradient(#1b1e21 1px,transparent 1px),linear-gradient(90deg,#1b1e21 1px,transparent 1px); background-size:32px 32px; }}
.link {{ fill:none; stroke:#5b5f63; stroke-width:2; stroke-opacity:.72; }}
.node-card {{ cursor:pointer; }}
.card-bg {{ fill:#292929; stroke:#505050; stroke-width:1.2; filter:drop-shadow(0 2px 2px rgba(0,0,0,.55)); }}
.card-title {{ fill:#4db7ff; font-size:14px; font-weight:600; }}
.card-meta {{ fill:#d8d8d8; font-size:12px; }}
.card-key {{ fill:#4db7ff; font-size:13px; }}
.card-value {{ fill:#e4e4e4; font-size:13px; }}
.card-number {{ fill:#ffc857; }}
.divider {{ stroke:#414141; stroke-width:1; }}
.toggle {{ fill:#333; stroke:#454545; }}
.toggle-text {{ fill:#aaa; font-size:12px; text-anchor:middle; }}
.node-card.search-match .card-bg {{ stroke:#ff9800; stroke-width:3px; }}
#controls {{ position:fixed; right:16px; bottom:16px; display:flex; gap:7px; z-index:10; }}
#controls button {{ width:38px; height:34px; border:1px solid #4a4d50; border-radius:6px; background:#26292c; color:#eee; font-size:18px; cursor:pointer; }}
#controls button.wide {{ width:auto; padding:0 12px; font:12px Arial,sans-serif; }}
#controls button:hover {{ background:#35393d; }}
.tooltip {{ position:absolute; display:none; background:rgba(20,20,20,.96); color:#eee; border:1px solid #555; padding:8px 10px; border-radius:5px; font:12px Arial,sans-serif; max-width:460px; pointer-events:none; z-index:20; }}
</style>
<script>{d3_source}</script>
</head>
<body>
<svg id="graph"></svg>
<div id="tooltip" class="tooltip"></div>
<div id="controls"><button onclick="zoomBy(1.25)" title="Zoom in">+</button><button onclick="zoomBy(0.8)" title="Zoom out">−</button><button class="wide" onclick="fitGraph()">Fit</button><button class="wide" onclick="focusRoot()">Root</button></div>
<script>
const rawNodes = {graph_json};
const byId = new Map(rawNodes.map(d => [d.id, d]));
rawNodes.forEach(d => {{ d.children=[]; d._children=[]; }});
let rootData=null;
rawNodes.forEach(d => {{ if(d.parentId===null) rootData=d; else {{ const p=byId.get(d.parentId); if(p) p.children.push(d); }} }});

// A display node represents one object/array as a card. Primitive children
// become rows inside that card, matching the compact reference design.
function makeDisplay(data) {{
  const kids=(data.children||[]);
  const structural=kids.filter(c => c.hasChildren || c.type==='object' || c.type==='array');
  const rows=kids.filter(c => !c.hasChildren && c.type!=='object' && c.type!=='array');
  return {{ data, rows, children:structural.map(makeDisplay), _children:[] }};
}}
let displayRoot = rootData ? makeDisplay(rootData) : null;
let depthLimit=999, labelsVisible=true;
const svg=d3.select('#graph');
const container=svg.append('g');
const linkLayer=container.append('g');
const nodeLayer=container.append('g');
const zoom=d3.zoom().scaleExtent([0.12,4]).on('zoom',e=>container.attr('transform',e.transform));
svg.call(zoom).on('dblclick.zoom',null);
const tooltip=d3.select('#tooltip');

function dims() {{ return [document.documentElement.clientWidth||window.innerWidth, document.documentElement.clientHeight||window.innerHeight]; }}
function visibleChildren(n) {{ if(n.depth>=depthLimit) return []; return n.children||[]; }}
function cardWidth(d) {{ return 235; }}
function cardHeight(d) {{ return 44 + Math.max(1,d.data.rows.length)*30 + (d.data.children.length?30:0); }}
function typeSummary(d) {{
 const t=d.data.data.type;
 if(t==='array') return `[${{(d.data.data.children||[]).length}} items]`;
 if(t==='object') return `{{${{(d.data.data.children||[]).length}} keys}}`;
 return '';
}}
function valueClass(r) {{ return (r.type==='integer'||r.type==='number') ? 'card-value card-number':'card-value'; }}
function update() {{
 if(!displayRoot) return;
 const root=d3.hierarchy(displayRoot,visibleChildren);
 const tree=d3.tree().nodeSize([Math.max(120, 54 + Math.max(...root.descendants().map(cardHeight))), 350]);
 tree(root);
 const nodes=root.descendants(), links=root.links();
 const link=linkLayer.selectAll('path').data(links,d=>d.target.data.data.id);
 link.exit().remove();
 link.enter().append('path').attr('class','link').merge(link).attr('d',d3.linkHorizontal().x(d=>d.y).y(d=>d.x));
 const node=nodeLayer.selectAll('g.node-card').data(nodes,d=>d.data.data.id);
 node.exit().remove();
 const enter=node.enter().append('g').attr('class','node-card');
 enter.append('rect').attr('class','card-bg').attr('rx',7).attr('ry',7);
 enter.append('text').attr('class','card-title');
 enter.append('text').attr('class','card-meta');
 const merged=enter.merge(node).attr('transform',d=>`translate(${{d.y}},${{d.x-cardHeight(d)/2}})`);
 merged.select('.card-bg').attr('width',cardWidth).attr('height',cardHeight);
 merged.select('.card-title').attr('x',14).attr('y',25).text(d=>labelsVisible?d.data.data.name:'');
 merged.select('.card-meta').attr('x',cardWidth-12).attr('y',25).attr('text-anchor','end').text(d=>typeSummary(d));
 merged.each(function(d) {{
   const g=d3.select(this); g.selectAll('.dynamic').remove();
   let y=44;
   d.data.rows.forEach(r=>{{
     g.append('line').attr('class','divider dynamic').attr('x1',0).attr('x2',cardWidth).attr('y1',y).attr('y2',y);
     g.append('text').attr('class','card-key dynamic').attr('x',14).attr('y',y+20).text(labelsVisible?r.name+':':'');
     const val=(r.value===null?'null':String(r.value));
     g.append('text').attr('class',valueClass(r)+' dynamic').attr('x',Math.min(112,18+r.name.length*8)).attr('y',y+20).text(val.length>18?val.slice(0,18)+'…':val);
     y+=30;
   }});
   if(d.data.children.length) {{
     g.append('line').attr('class','divider dynamic').attr('x1',0).attr('x2',cardWidth).attr('y1',y).attr('y2',y);
     g.append('rect').attr('class','toggle dynamic').attr('x',12).attr('y',y+7).attr('width',18).attr('height',18).attr('rx',3);
     g.append('text').attr('class','toggle-text dynamic').attr('x',21).attr('y',y+20).text((d.data.children&&d.data.children.length)?'−':'+');
     g.append('text').attr('class','card-key dynamic').attr('x',38).attr('y',y+20).text(`${{d.data.children.length}} nested node${{d.data.children.length===1?'':'s'}}`);
   }}
 }});
 merged.on('click',(event,d)=>{{ event.stopPropagation(); const x=d.data; if(x.children&&x.children.length){{x._children=x.children;x.children=[];}}else if(x._children&&x._children.length){{x.children=x._children;x._children=[];}} update(); }});
 merged.on('mouseover',(event,d)=>tooltip.style('display','block').html(`<b>${{escapeHtml(d.data.data.path)}}</b><br>Type: ${{escapeHtml(d.data.data.type)}}`))
 .on('mousemove',event=>tooltip.style('left',(event.pageX+12)+'px').style('top',(event.pageY+12)+'px')).on('mouseout',()=>tooltip.style('display','none'));
}}
function escapeHtml(v) {{ const e=document.createElement('div'); e.textContent=String(v); return e.innerHTML; }}
function fitGraph() {{ const b=container.node().getBBox(); if(!b.width||!b.height)return; const [w,h]=dims(); const s=Math.min(.95,Math.min((w-80)/b.width,(h-80)/b.height)); const x=(w-b.width*s)/2-b.x*s, y=(h-b.height*s)/2-b.y*s; svg.transition().duration(300).call(zoom.transform,d3.zoomIdentity.translate(x,y).scale(s)); }}
function focusRoot() {{ if(!displayRoot)return; const [w,h]=dims(); svg.transition().duration(250).call(zoom.transform,d3.zoomIdentity.translate(55,h/2).scale(.9)); }}
function zoomBy(k) {{ svg.transition().duration(180).call(zoom.scaleBy,k); }}
function resetGraph() {{ expandAll(); depthLimit=999; update(); focusRoot(); }}
function searchGraph(q) {{ const n=String(q||'').trim().toLowerCase(); nodeLayer.selectAll('g.node-card').classed('search-match',false); if(!n)return; nodeLayer.selectAll('g.node-card').classed('search-match',d=>{{ const x=d.data.data; return String(x.name).toLowerCase().includes(n)||String(x.path).toLowerCase().includes(n)||d.data.rows.some(r=>String(r.name).toLowerCase().includes(n)||String(r.value).toLowerCase().includes(n)); }}); }}
function walk(n,fn) {{ fn(n); [...(n.children||[]),...(n._children||[])].forEach(c=>walk(c,fn)); }}
function collapseAll() {{ if(!displayRoot)return; walk(displayRoot,n=>{{if(n!==displayRoot&&n.children&&n.children.length){{n._children=n.children;n.children=[];}}}}); update(); focusRoot(); }}
function expandAll() {{ if(!displayRoot)return; walk(displayRoot,n=>{{if(n._children&&n._children.length){{n.children=n._children;n._children=[];}}}}); update(); }}
function setDepth(d) {{ depthLimit=Number(d); update(); }}
function setLabels(v) {{ labelsVisible=Boolean(v); update(); }}
function exportSvgMarkup() {{
  if (!displayRoot) return null;
  const source = document.getElementById('graph');
  const clone = source.cloneNode(true);
  const box = container.node().getBBox();
  const pad = 30;
  const width = Math.max(1, Math.ceil(box.width + pad * 2));
  const height = Math.max(1, Math.ceil(box.height + pad * 2));
  clone.setAttribute('width', width);
  clone.setAttribute('height', height);
  clone.setAttribute('viewBox', `${{box.x-pad}} ${{box.y-pad}} ${{width}} ${{height}}`);
  clone.removeAttribute('style');
  const style = document.createElementNS('http://www.w3.org/2000/svg','style');
  style.textContent = `
    svg {{ background:#111315; font-family:Consolas, 'Courier New', monospace; }}
    .link {{ fill:none; stroke:#5b5f63; stroke-width:2; stroke-opacity:.72; }}
    .card-bg {{ fill:#292929; stroke:#505050; stroke-width:1.2; }}
    .card-title {{ fill:#54b7ff; font-size:14px; font-weight:600; }}
    .card-meta {{ fill:#b8bdc2; font-size:12px; }}
    .card-key {{ fill:#54b7ff; font-size:13px; }}
    .card-value {{ fill:#e2e5e8; font-size:13px; }}
    .card-number {{ fill:#ffd166; }}
    .divider {{ stroke:#45484b; stroke-width:1; }}
    .toggle {{ fill:#303235; stroke:#45484b; }}
    .toggle-text {{ fill:#c9cdd1; font-size:13px; text-anchor:middle; }}
  `;
  clone.insertBefore(style, clone.firstChild);
  return new XMLSerializer().serializeToString(clone);
}}
update();
requestAnimationFrame(()=>requestAnimationFrame(focusRoot));
window.addEventListener('resize',()=>focusRoot());
</script>
</body>
</html>
"""

    def _run_js(
        self,
        script: str,
    ) -> None:
        """Execute JavaScript in graph."""

        self._web_view.page().runJavaScript(script)

    def _search_graph(self) -> None:
        """Highlight matching graph nodes."""

        query = json.dumps(self._search.text())

        self._run_js(f"searchGraph({query});")

    def _reset_graph(self) -> None:
        """Reset graph state."""

        self._search.clear()

        self._depth_slider.setValue(self._depth_slider.maximum())

        self._labels_checkbox.setChecked(True)

        self._run_js("resetGraph();")

    def _fit_graph(self) -> None:
        """Fit graph to viewport."""

        self._run_js("fitGraph();")

    def _expand_all(self) -> None:
        """Expand graph nodes."""

        self._run_js("expandAll();")

    def _collapse_all(self) -> None:
        """Collapse graph nodes."""

        self._run_js("collapseAll();")

    def _depth_changed(
        self,
        depth: int,
    ) -> None:
        """Change visible graph depth."""

        self._depth_value.setText(str(depth))

        self._run_js(f"setDepth({depth});")

    def _toggle_labels(
        self,
        visible: bool,
    ) -> None:
        """Show or hide graph labels."""

        javascript_value = "true" if visible else "false"

        self._run_js(f"setLabels({javascript_value});")

    def export_graph(
        self,
        file_name: str,
        on_success=None,
        on_error=None,
    ) -> None:
        """Export the complete rendered graph as SVG, PNG, or PDF."""

        if self._graph_data is None:
            if on_error is not None:
                on_error("Load JSON before exporting the graph.")
            return

        path = os.path.abspath(file_name)
        extension = os.path.splitext(path)[1].lower()

        if extension not in {".svg", ".png", ".pdf"}:
            if on_error is not None:
                on_error(f"Unsupported graph export format: {extension}")
            return

        def receive_svg(svg_markup):
            try:
                if not svg_markup:
                    raise RuntimeError("The graph did not return SVG data.")

                os.makedirs(os.path.dirname(path), exist_ok=True)
                svg_bytes = svg_markup.encode("utf-8")

                if extension == ".svg":
                    with open(path, "wb") as handle:
                        handle.write(svg_bytes)
                else:
                    renderer = QSvgRenderer(QByteArray(svg_bytes))
                    if not renderer.isValid():
                        raise RuntimeError("Unable to render the graph SVG.")

                    size = renderer.defaultSize()
                    width = max(size.width(), 1)
                    height = max(size.height(), 1)

                    if extension == ".png":
                        image = QImage(
                            width,
                            height,
                            QImage.Format.Format_ARGB32,
                        )
                        image.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(image)
                        renderer.render(painter)
                        painter.end()

                        if not image.save(path, "PNG"):
                            raise RuntimeError("Unable to save graph PNG.")
                    else:
                        writer = QPdfWriter(path)
                        writer.setResolution(96)
                        painter = QPainter(writer)
                        renderer.render(painter)
                        painter.end()

                if not os.path.isfile(path):
                    raise RuntimeError(f"Graph export did not create the file: {path}")

                if on_success is not None:
                    on_success(path)

            except Exception as error:
                if on_error is not None:
                    on_error(str(error))

        self._web_view.page().runJavaScript(
            "exportSvgMarkup();",
            receive_svg,
        )

    def _toggle_fullscreen(self) -> None:
        """Toggle graph fullscreen mode."""

        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
