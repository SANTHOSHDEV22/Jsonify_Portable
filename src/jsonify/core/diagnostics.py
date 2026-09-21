"""Parsing time, memory and structure diagnostics for a JSON document."""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from dataclasses import dataclass

from jsonify.core.models import JSONValue
from jsonify.core.traversal import calculate_json_stats


@dataclass(frozen=True, slots=True)
class Diagnostics:
    """Measurements taken while parsing one document."""

    size_bytes: int
    parse_ms: float
    parse_peak_bytes: int
    deep_size_bytes: int
    node_count: int
    max_depth: int
    objects: int
    arrays: int
    keys: int

    def format(self) -> str:
        """Human-readable multi-line report."""

        throughput = (
            (self.size_bytes / 1_048_576) / (self.parse_ms / 1000) if self.parse_ms else 0.0
        )
        return "\n".join(
            [
                f"Document size:        {_bytes(self.size_bytes)}",
                f"Parse time:           {self.parse_ms:.2f} ms  ({throughput:.1f} MB/s)",
                f"Peak memory (parse):  {_bytes(self.parse_peak_bytes)}",
                f"In-memory size:       {_bytes(self.deep_size_bytes)} (approx.)",
                f"Nodes:                {self.node_count:,}",
                f"Objects / arrays:     {self.objects:,} / {self.arrays:,}",
                f"Distinct keys:        {self.keys:,}",
                f"Maximum depth:        {self.max_depth}",
            ]
        )


def measure_document(text: str) -> tuple[Diagnostics, JSONValue]:
    """Parse ``text`` while measuring time and memory; returns (report, value).

    Raises ``json.JSONDecodeError`` for invalid JSON.
    """

    size_bytes = len(text.encode("utf-8"))

    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    tracemalloc.reset_peak()
    baseline, _ = tracemalloc.get_traced_memory()

    started = time.perf_counter()
    try:
        value = json.loads(text)
    finally:
        parse_ms = (time.perf_counter() - started) * 1000
        _, peak = tracemalloc.get_traced_memory()
        if not was_tracing:
            tracemalloc.stop()

    stats = calculate_json_stats(value)
    report = Diagnostics(
        size_bytes=size_bytes,
        parse_ms=parse_ms,
        parse_peak_bytes=max(0, peak - baseline),
        deep_size_bytes=deep_size(value),
        node_count=stats["objects"] + stats["arrays"] + stats["leaves"],
        max_depth=stats["max_depth"],
        objects=stats["objects"],
        arrays=stats["arrays"],
        keys=stats["keys"],
    )
    return report, value


def deep_size(value: JSONValue) -> int:
    """Approximate the in-memory size of a parsed JSON value (iterative)."""

    total = 0
    stack: list[JSONValue] = [value]
    seen: set[int] = set()

    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        total += sys.getsizeof(node)

        if isinstance(node, dict):
            for key, child in node.items():
                if id(key) not in seen:
                    seen.add(id(key))
                    total += sys.getsizeof(key)
                stack.append(child)
        elif isinstance(node, list):
            stack.extend(node)

    return total


def _bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024**2:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024**2:.2f} MB"
