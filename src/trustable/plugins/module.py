from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from trustable.config.schema import ModuleConfig

ModuleFactory = Callable[[ModuleConfig], object]


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    factory: ModuleFactory
    config_model: type[ModuleConfig]
    priority: int = 100
