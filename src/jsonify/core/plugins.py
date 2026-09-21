"""A deliberately small plugin system for converters, analyzers and tools.

Plugins are discovered from two places:
    * installed packages exposing an entry point in the ``jsonify.plugins`` group, and
    * ``*.py`` files inside the ``plugins`` folder of Jsonify's data directory.

Either way, a plugin provides a ``register(registry)`` callable that adds
things to the :class:`PluginRegistry`::

    def register(registry):
        registry.register_converter("TOML", to_json=toml_to_json, from_json=json_to_toml)
        registry.register_analyzer("No empty names", find_empty_names)
        registry.register_tool("Reverse", lambda text: text[::-1])

A plugin that fails to load never takes the application down; the error is
recorded in :attr:`PluginRegistry.errors` instead.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from jsonify.core.models import JSONValue

ENTRY_POINT_GROUP = "jsonify.plugins"


@dataclass(frozen=True, slots=True)
class ConverterPlugin:
    """A named format that can convert to and/or from JSON."""

    name: str
    to_json: Callable[[str], JSONValue] | None = None
    from_json: Callable[[JSONValue], str] | None = None


class PluginRegistry:
    """Everything registered by plugins."""

    def __init__(self) -> None:
        self.converters: dict[str, ConverterPlugin] = {}
        self.analyzers: dict[str, Callable[[JSONValue], list[str]]] = {}
        self.tools: dict[str, Callable[[str], str]] = {}
        self.errors: list[str] = []
        self.loaded: list[str] = []

    def register_converter(
        self,
        name: str,
        *,
        to_json: Callable[[str], JSONValue] | None = None,
        from_json: Callable[[JSONValue], str] | None = None,
    ) -> None:
        if to_json is None and from_json is None:
            raise ValueError("A converter needs at least one of to_json / from_json.")
        self.converters[name] = ConverterPlugin(name, to_json, from_json)

    def register_analyzer(self, name: str, func: Callable[[JSONValue], list[str]]) -> None:
        self.analyzers[name] = func

    def register_tool(self, name: str, func: Callable[[str], str]) -> None:
        self.tools[name] = func

    def run_analyzers(self, payload: JSONValue) -> dict[str, list[str]]:
        """Run every analyzer; failures are reported as a single finding."""

        results: dict[str, list[str]] = {}
        for name, analyzer in self.analyzers.items():
            try:
                findings = list(analyzer(payload))
            except Exception as error:  # noqa: BLE001 - plugin code is untrusted
                findings = [f"Analyzer failed: {error}"]
            if findings:
                results[name] = [str(item) for item in findings]
        return results

    def load(self, plugin_dir: Path | None = None) -> None:
        """Discover and register plugins (safe to call more than once)."""

        self._load_entry_points()
        if plugin_dir is not None:
            self._load_directory(plugin_dir)

    # -----------------------------------------------------------------

    def _load_entry_points(self) -> None:
        try:
            entry_points = metadata.entry_points(group=ENTRY_POINT_GROUP)
        except Exception as error:  # noqa: BLE001
            self.errors.append(f"Could not read plugin entry points: {error}")
            return

        for entry_point in entry_points:
            label = f"entry point '{entry_point.name}'"
            if label in self.loaded:
                continue
            try:
                register = entry_point.load()
                register(self)
            except Exception as error:  # noqa: BLE001
                self.errors.append(f"{label}: {error}")
            else:
                self.loaded.append(label)

    def _load_directory(self, plugin_dir: Path) -> None:
        if not plugin_dir.is_dir():
            return

        for path in sorted(plugin_dir.glob("*.py")):
            label = f"file '{path.name}'"
            if label in self.loaded:
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"jsonify_plugin_{path.stem}", path)
                if spec is None or spec.loader is None:
                    raise ImportError("cannot create module spec")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                register = getattr(module, "register", None)
                if not callable(register):
                    raise AttributeError("plugin has no register(registry) function")
                register(self)
            except Exception as error:  # noqa: BLE001
                self.errors.append(f"{label}: {error}")
            else:
                self.loaded.append(label)


_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Return the process-wide plugin registry (created empty on first use)."""

    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
