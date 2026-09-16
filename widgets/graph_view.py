"""
widgets/graph_view.py
-----------------------
Builds a jsoncrack.com-style graph: rich HTML "cards" (one per object),
each listing its own scalar fields as rows, connected to child cards
for nested objects/arrays with curved connector lines — laid out with
D3's hierarchical TREE layout (d3.tree / Reingold-Tilford), the same
family of algorithm jsoncrack itself uses. This is deterministic and
STATIC: every node gets one fixed position, computed once, left to
right by depth. There is no physics simulation and nodes are not
draggable — only the whole canvas pans (click+drag empty space) and
zooms (scroll wheel, or the +/-/fit toolbar buttons).

This does NOT use pyvis. It builds two things:
  1. A flat node list in Python (`build_graph_data`), where every node
     (except the root) carries a `parent_id` and an `edge_label` — the
     JSON payload is inherently a tree, so this is all D3 needs to
     reconstruct the hierarchy via `d3.stratify()`.
  2. A self-contained HTML document (`build_graph_html`) that embeds a
     bundled copy of D3.js (see `_d3_source.py`, no CDN needed) plus
     hand-written layout/rendering JS, and the node data as a JSON blob.

How a JSON payload maps to cards
---------------------------------
- Each dict becomes one card. Scalar keys (str/int/float/bool/None)
  become plain rows: "key: value". Keys whose value is a dict or a
  list become a summary row ("- key: {n keys}" / "- key: [n items]")
  *and* spawn a separate connected card (or cards, for a list).
- A list does not get its own card: each of its items becomes a card
  directly connected to the *parent* card, with the edge labeled by
  the list's own key (repeated once per item) — this matches
  jsoncrack's look, where "fruits: [3 items]" fans out into three
  separate fruit cards via three edges all labeled "fruits".
- A string value that looks like a hex color (e.g. "#FF0000") gets a
  small color swatch next to it in its row.
"""
from __future__ import annotations

import itertools
import json
import re
from typing import Any, Dict, Iterator, List, Optional

from widgets._d3_source import D3_JS

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")


def _fmt_scalar(value: Any) -> str:
    """Render a scalar value as display text (unquoted strings, JSON otherwise)."""
    return value if isinstance(value, str) else json.dumps(value)


def _scalar_row(key: str, value: Any) -> dict:
    row = {"type": "scalar", "key": key, "value": _fmt_scalar(value)}
    if isinstance(value, str) and _HEX_COLOR_RE.match(value):
        row["color"] = value
    return row


def _build_dict_node(
    data: dict,
    parent_id: Optional[int],
    edge_label: Optional[str],
    counter: Iterator[int],
    nodes: List[dict],
) -> int:
    """Recursively turn a dict into one card node (+ child cards), return its id."""
    node_id = next(counter)
    rows: List[dict] = []

    for key, value in data.items():
        if isinstance(value, dict):
            rows.append({"type": "summary", "key": key, "value": f"{{{len(value)} keys}}"})
            _build_dict_node(value, node_id, key, counter, nodes)

        elif isinstance(value, list):
            rows.append({"type": "summary", "key": key, "value": f"[{len(value)} items]"})
            _build_list_children(value, key, node_id, counter, nodes)

        else:
            rows.append(_scalar_row(key, value))

    nodes.append({"id": node_id, "parent_id": parent_id, "edge_label": edge_label, "rows": rows})
    return node_id


def _build_list_children(
    items: list,
    label: str,
    parent_id: int,
    counter: Iterator[int],
    nodes: List[dict],
) -> None:
    """Connect each item of a list directly to `parent_id`, edge labeled `label`."""
    for item in items:
        if isinstance(item, dict):
            _build_dict_node(item, parent_id, label, counter, nodes)

        elif isinstance(item, list):
            # A list of lists: flatten one level, same parent/label.
            _build_list_children(item, label, parent_id, counter, nodes)

        else:
            child_id = next(counter)
            nodes.append(
                {"id": child_id, "parent_id": parent_id, "edge_label": label, "rows": [_scalar_row("value", item)]}
            )


def build_graph_data(payload: Any) -> Dict[str, list]:
    """Convert a parsed JSON payload into {"nodes": [...]}, a flat, single-rooted tree.

    Every node has "id"; every node except the root also has "parent_id"
    (pointing at its parent's id) and "edge_label" (the key name to show
    on the connecting line). This shape is exactly what `d3.stratify()`
    needs to rebuild the hierarchy client-side.

    Example:
        >>> data = build_graph_data({"a": 1, "b": {"c": 2}})
        >>> len(data["nodes"])
        2
        >>> data["nodes"][1]["parent_id"] is not None
        True
    """
    counter = itertools.count()
    nodes: List[dict] = []

    if isinstance(payload, dict):
        _build_dict_node(payload, None, None, counter, nodes)
    elif isinstance(payload, list):
        root_id = next(counter)
        nodes.append(
            {
                "id": root_id,
                "parent_id": None,
                "edge_label": None,
                "rows": [{"type": "summary", "key": "root", "value": f"[{len(payload)} items]"}],
            }
        )
        _build_list_children(payload, "root", root_id, counter, nodes)
    else:
        root_id = next(counter)
        nodes.append({"id": root_id, "parent_id": None, "edge_label": None, "rows": [_scalar_row("value", payload)]})

    return {"nodes": nodes}


_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{
    margin: 0; padding: 0; width: 100%; height: 100%;
    background: #0d1117; overflow: hidden;
    font-family: Consolas, Menlo, 'Courier New', monospace;
  }}
  #stage {{ position: relative; width: 100%; height: 100%; overflow: hidden; cursor: grab; }}
  #stage.grabbing {{ cursor: grabbing; }}
  #zoom-layer {{ position: absolute; top: 0; left: 0; transform-origin: 0 0; }}
  svg#edges {{ position: absolute; top: 0; left: 0; overflow: visible; pointer-events: none; }}
  .edge-path {{ fill: none; stroke: #4b5563; stroke-width: 1.5px; }}
  .edge-label {{
    fill: #9ca3af; font-size: 12px;
    paint-order: stroke; stroke: #0d1117; stroke-width: 3px; stroke-linejoin: round;
  }}
  .node-card {{
    position: absolute; top: 0; left: 0;
    background: #161b22; border: 1px solid #30363d; border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.45);
    padding: 8px 10px; font-size: 13px; color: #e6edf3;
    min-width: 110px; user-select: none;
  }}
  .node-row {{ white-space: nowrap; padding: 1px 0; }}
  .node-row .k {{ color: #79c0ff; }}
  .node-row .v {{ color: #a5d6ff; margin-left: 4px; }}
  .node-row.summary .k {{ color: #d2a8ff; }}
  .swatch {{
    display: inline-block; width: 10px; height: 10px; border-radius: 2px;
    margin-right: 4px; vertical-align: middle; border: 1px solid rgba(255,255,255,0.35);
  }}
  .toolbar {{ position: absolute; bottom: 14px; left: 14px; display: flex; gap: 6px; z-index: 10; }}
  .toolbar button {{
    background: #21262d; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px;
    width: 32px; height: 32px; cursor: pointer; font-size: 16px; line-height: 1;
  }}
  .toolbar button:hover {{ background: #30363d; }}
</style>
</head>
<body>
<div id="stage">
  <div id="zoom-layer">
    <svg id="edges"><g id="edges-g"></g></svg>
    <div id="nodes-layer"></div>
  </div>
  <div class="toolbar">
    <button id="zoom-in" title="Zoom in">+</button>
    <button id="zoom-out" title="Zoom out">&minus;</button>
    <button id="zoom-fit" title="Fit to view">&#10021;</button>
  </div>
</div>

<script>{d3_js}</script>
<script>
const DATA = {data_json};

// ---- constants controlling the static tree layout ----
const LEVEL_GAP = 360;   // horizontal pixel gap between depth levels (columns)
const SIBLING_PAD = 28;  // extra vertical pixel gap between adjacent cards
const MARGIN_X = 60;     // left margin before the root card
const MARGIN_Y = 60;     // top margin above the topmost card

function escapeHtml(s) {{
  return String(s).replace(/[&<>"']/g, c => ({{
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }}[c]));
}}

// ---- 1. build one DOM card per node (positions set later) ----
const nodesLayer = document.getElementById('nodes-layer');
const nodeEls = {{}};

DATA.nodes.forEach(n => {{
  const el = document.createElement('div');
  el.className = 'node-card';
  n.rows.forEach(r => {{
    const row = document.createElement('div');
    row.className = 'node-row' + (r.type === 'summary' ? ' summary' : '');
    let html = '';
    if (r.color) html += `<span class="swatch" style="background:${{r.color}}"></span>`;
    const prefix = r.type === 'summary' ? '- ' : '';
    html += `<span class="k">${{prefix}}${{escapeHtml(r.key)}}:</span><span class="v">${{escapeHtml(r.value)}}</span>`;
    row.innerHTML = html;
    el.appendChild(row);
  }});
  nodesLayer.appendChild(el);
  nodeEls[n.id] = el;
}});

// ---- 2. rebuild the hierarchy D3-side from the flat parent_id list ----
const root = d3.stratify()
  .id(d => d.id)
  .parentId(d => d.parent_id)
  (DATA.nodes);

// Measure each card's real rendered size now that it's in the DOM.
root.each(d => {{
  const el = nodeEls[d.id];
  d.measuredWidth = el.offsetWidth;
  d.measuredHeight = el.offsetHeight;
}});

// ---- 3. compute a STATIC tree layout (Reingold-Tilford), once ----
// nodeSize([1, LEVEL_GAP]) makes each "unit" of vertical separation equal
// to exactly 1 pixel, so the separation() function below can return real
// pixel gaps directly (based on each card's actual measured height) —
// this is what keeps taller/shorter cards from overlapping or leaving
// uneven gaps, without needing a physics simulation to sort it out.
const treeLayout = d3.tree()
  .nodeSize([1, LEVEL_GAP])
  .separation((a, b) => {{
    const gap = (a.measuredHeight + b.measuredHeight) / 2 + SIBLING_PAD;
    return gap;
  }});

treeLayout(root);

// d3.tree() lays out top-to-bottom (x = breadth, y = depth). We want
// left-to-right like jsoncrack, so on screen: screenX = d.y, screenY = d.x.
let minX = Infinity;
root.each(d => {{ if (d.x < minX) minX = d.x; }});
const offsetY = MARGIN_Y - minX;
const offsetX = MARGIN_X;

// ---- 4. position every card ----
root.each(d => {{
  const el = nodeEls[d.id];
  const left = d.y + offsetX;
  const top = d.x + offsetY - d.measuredHeight / 2;
  el.style.transform = `translate(${{left}}px, ${{top}}px)`;
  d.screenLeft = left;
  d.screenTop = top;
  d.screenRight = left + d.measuredWidth;
  d.screenMidY = top + d.measuredHeight / 2;
}});

// ---- 5. draw curved edges (right edge of parent -> left edge of child) ----
const edgesG = document.getElementById('edges-g');
const linkGen = d3.linkHorizontal().x(p => p.x).y(p => p.y);

root.links().forEach(link => {{
  const sourcePoint = {{ x: link.source.screenRight, y: link.source.screenMidY }};
  const targetPoint = {{ x: link.target.screenLeft, y: link.target.screenMidY }};

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('class', 'edge-path');
  path.setAttribute('d', linkGen({{ source: sourcePoint, target: targetPoint }}));
  edgesG.appendChild(path);

  const labelText = link.target.data.edge_label;
  if (labelText) {{
    // Anchor the label just before the target card starts, right-aligned,
    // rather than at a path midpoint — this guarantees the label text
    // (which extends in its writing direction from its anchor) never
    // gets drawn underneath/behind the target card, and naturally
    // spreads labels out by each edge's distinct target Y position.
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('class', 'edge-label');
    label.setAttribute('text-anchor', 'end');
    label.setAttribute('x', targetPoint.x - 10);
    label.setAttribute('y', targetPoint.y - 4);
    label.textContent = labelText;
    edgesG.appendChild(label);
  }}
}});

// ---- 6. pan + zoom on the whole canvas (nodes themselves are static) ----
const zoomLayer = document.getElementById('zoom-layer');
const zoom = d3.zoom()
  .scaleExtent([0.1, 4])
  .on('zoom', (event) => {{
    zoomLayer.style.transform = `translate(${{event.transform.x}}px, ${{event.transform.y}}px) scale(${{event.transform.k}})`;
  }});

const stage = d3.select('#stage');
stage.call(zoom);

document.getElementById('zoom-in').onclick = () =>
  stage.transition().duration(200).call(zoom.scaleBy, 1.3);
document.getElementById('zoom-out').onclick = () =>
  stage.transition().duration(200).call(zoom.scaleBy, 0.75);
document.getElementById('zoom-fit').onclick = fitToView;

function fitToView() {{
  const nodes = root.descendants();
  if (nodes.length === 0) return;
  const pad = 60;
  const minLeft = Math.min(...nodes.map(d => d.screenLeft)) - pad;
  const maxRight = Math.max(...nodes.map(d => d.screenRight)) + pad;
  const minTop = Math.min(...nodes.map(d => d.screenTop)) - pad;
  const maxBottom = Math.max(...nodes.map(d => d.screenTop + d.measuredHeight)) + pad;
  const w = Math.max(maxRight - minLeft, 1), h = Math.max(maxBottom - minTop, 1);
  const stageEl = document.getElementById('stage');
  const scale = Math.min(stageEl.clientWidth / w, stageEl.clientHeight / h, 1.5);
  const tx = stageEl.clientWidth / 2 - scale * (minLeft + w / 2);
  const ty = stageEl.clientHeight / 2 - scale * (minTop + h / 2);
  stage.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}}

fitToView();
</script>
</body>
</html>
"""


def build_graph_html(payload: Any) -> str:
    """Build a static, jsoncrack-style hierarchical tree graph as standalone HTML.

    Args:
        payload: Any JSON-compatible Python value (the parsed payload).

    Returns:
        A full, self-contained HTML document (D3.js is embedded inline,
        no CDN or external files needed) — pass into
        QWebEngineView.setHtml(...) or write it to a file directly.
    """
    data = build_graph_data(payload)
    return _HTML_TEMPLATE.format(d3_js=D3_JS, data_json=json.dumps(data))