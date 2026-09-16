"""Advanced graph preparation service for Jsonify."""

from __future__ import annotations

from dataclasses import dataclass

from jsonify.core.models import JSONValue


@dataclass(frozen=True, slots=True)
class GraphStatistics:
    """Statistics describing a JSON graph."""

    total_nodes: int
    object_nodes: int
    array_nodes: int
    primitive_nodes: int
    max_depth: int


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Serializable graph node."""

    node_id: int
    parent_id: int | None
    name: str
    path: str
    node_type: str
    value: str
    depth: int
    has_children: bool


@dataclass(frozen=True, slots=True)
class GraphData:
    """Prepared graph data."""

    nodes: tuple[GraphNode, ...]
    statistics: GraphStatistics
    truncated: bool


class AdvancedGraphService:
    """Prepare JSON data for advanced graph visualization."""

    def __init__(
        self,
        *,
        node_limit: int = 5_000,
        preview_length: int = 80,
    ) -> None:
        self.node_limit = node_limit
        self.preview_length = preview_length

    def build(
        self,
        payload: JSONValue,
    ) -> GraphData:
        """Build graph data without recursively traversing Python."""

        nodes: list[GraphNode] = []

        object_nodes = 0
        array_nodes = 0
        primitive_nodes = 0
        max_depth = 0
        truncated = False

        next_id = 0

        stack: list[
            tuple[
                JSONValue,
                str,
                str,
                int | None,
                int,
            ]
        ] = [
            (
                payload,
                "$",
                "$",
                None,
                0,
            )
        ]

        while stack:
            if len(nodes) >= self.node_limit:
                truncated = True
                break

            (
                value,
                name,
                path,
                parent_id,
                depth,
            ) = stack.pop()

            node_id = next_id
            next_id += 1

            node_type = self._type_name(
                value
            )

            if isinstance(value, dict):
                object_nodes += 1
            elif isinstance(value, list):
                array_nodes += 1
            else:
                primitive_nodes += 1

            max_depth = max(
                max_depth,
                depth,
            )

            nodes.append(
                GraphNode(
                    node_id=node_id,
                    parent_id=parent_id,
                    name=name,
                    path=path,
                    node_type=node_type,
                    value=self._preview(value),
                    depth=depth,
                    has_children=self._has_children(
                        value
                    ),
                )
            )

            children = self._children(
                value,
                path,
            )

            # Reverse because this is a LIFO stack.
            for (
                child_value,
                child_name,
                child_path,
            ) in reversed(children):
                stack.append(
                    (
                        child_value,
                        child_name,
                        child_path,
                        node_id,
                        depth + 1,
                    )
                )

        statistics = GraphStatistics(
            total_nodes=len(nodes),
            object_nodes=object_nodes,
            array_nodes=array_nodes,
            primitive_nodes=primitive_nodes,
            max_depth=max_depth,
        )

        return GraphData(
            nodes=tuple(nodes),
            statistics=statistics,
            truncated=truncated,
        )

    def _children(
        self,
        value: JSONValue,
        path: str,
    ) -> list[
        tuple[
            JSONValue,
            str,
            str,
        ]
    ]:
        """Return direct JSON children."""

        children: list[
            tuple[
                JSONValue,
                str,
                str,
            ]
        ] = []

        if isinstance(value, dict):
            for key, child in value.items():
                children.append(
                    (
                        child,
                        key,
                        self._object_path(
                            path,
                            key,
                        ),
                    )
                )

        elif isinstance(value, list):
            for index, child in enumerate(
                value
            ):
                children.append(
                    (
                        child,
                        f"[{index}]",
                        f"{path}[{index}]",
                    )
                )

        return children

    def _preview(
        self,
        value: JSONValue,
    ) -> str:
        """Create a short node value."""

        if isinstance(value, dict):
            return (
                f"{len(value)} properties"
            )

        if isinstance(value, list):
            return (
                f"{len(value)} items"
            )

        if value is None:
            return "null"

        if isinstance(value, bool):
            return (
                "true"
                if value
                else "false"
            )

        text = str(value)

        if len(text) > self.preview_length:
            return (
                text[: self.preview_length]
                + "..."
            )

        return text

    @staticmethod
    def _has_children(
        value: JSONValue,
    ) -> bool:
        """Return whether a node has children."""

        return (
            isinstance(value, (dict, list))
            and bool(value)
        )

    @staticmethod
    def _type_name(
        value: JSONValue,
    ) -> str:
        """Return JSON type name."""

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

    @staticmethod
    def _object_path(
        parent: str,
        key: str,
    ) -> str:
        """Create a JSON-style object path."""

        if key.isidentifier():
            return f"{parent}.{key}"

        escaped = (
            key.replace("\\", "\\\\")
            .replace('"', '\\"')
        )

        return (
            f'{parent}["{escaped}"]'
        )