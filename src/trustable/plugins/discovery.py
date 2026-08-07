from __future__ import annotations

import importlib
from dataclasses import dataclass
from importlib import metadata

from trustable.config.schema import TrustableConfig
from trustable.modules.builtins import register_builtins
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry

ENTRY_POINT_GROUP = "trustable.modules"


@dataclass
class DiscoveryError:
    source: str  # "entry_point" | "config"
    ref: str
    message: str


def _resolve_ref(ref: str) -> object:
    module_path, _, attr = ref.partition(":")
    if not attr:
        raise ValueError(f"plugin ref must be 'module:attr', got '{ref}'")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def _coerce_spec(target: object) -> ModuleSpec:
    obj = target() if callable(target) and not isinstance(target, ModuleSpec) else target
    if not isinstance(obj, ModuleSpec):
        raise TypeError("plugin did not resolve to a ModuleSpec")
    return obj


def discover_modules(
    config: TrustableConfig, registry: ModuleRegistry
) -> list[DiscoveryError]:
    errors: list[DiscoveryError] = []

    register_builtins(registry)

    for ep in metadata.entry_points(group=ENTRY_POINT_GROUP):
        try:
            registry.register(_coerce_spec(ep.load()), source="entry_point")
        except Exception as exc:  # noqa: BLE001 - discovery must be resilient
            errors.append(DiscoveryError("entry_point", ep.value, str(exc)))

    for plugin in config.plugins:
        try:
            registry.register(_coerce_spec(_resolve_ref(plugin.ref)), source="config")
        except Exception as exc:  # noqa: BLE001 - discovery must be resilient
            errors.append(DiscoveryError("config", plugin.ref, str(exc)))

    return errors
