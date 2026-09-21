"""Utilities for analyzing large JSON payloads."""

from __future__ import annotations

from dataclasses import dataclass

from jsonify.core.models import JSONValue


@dataclass(frozen=True, slots=True)
class JsonSizeInfo:
    """Structural information about a JSON payload."""

    total_nodes: int
    containers: int
    primitives: int
    max_depth: int

    @property
    def is_large(self) -> bool:
        """Return whether lazy rendering is recommended."""

        return self.total_nodes >= 10_000


def analyze_json(
    payload: JSONValue,
) -> JsonSizeInfo:
    """Analyze the structural size of a JSON payload."""

    total_nodes = 0
    containers = 0
    primitives = 0
    max_depth = 0

    stack: list[tuple[JSONValue, int]] = [(payload, 0)]

    while stack:
        value, depth = stack.pop()

        total_nodes += 1
        max_depth = max(
            max_depth,
            depth,
        )

        if isinstance(value, dict):
            containers += 1

            for child in value.values():
                stack.append(
                    (
                        child,
                        depth + 1,
                    )
                )

        elif isinstance(value, list):
            containers += 1

            for child in value:
                stack.append(
                    (
                        child,
                        depth + 1,
                    )
                )

        else:
            primitives += 1

    return JsonSizeInfo(
        total_nodes=total_nodes,
        containers=containers,
        primitives=primitives,
        max_depth=max_depth,
    )
