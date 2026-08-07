from __future__ import annotations

from dataclasses import dataclass

from trustable.plugins.module import ModuleSpec


class DuplicateModuleError(Exception):
    """Raised when two modules register under the same name."""


@dataclass(frozen=True)
class RegisteredModule:
    spec: ModuleSpec
    source: str  # "builtin" | "entry_point" | "config"


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, RegisteredModule] = {}

    def register(self, spec: ModuleSpec, source: str = "builtin") -> None:
        if spec.name in self._modules:
            raise DuplicateModuleError(f"module '{spec.name}' is already registered")
        self._modules[spec.name] = RegisteredModule(spec=spec, source=source)

    def get(self, name: str) -> ModuleSpec:
        return self._modules[name].spec

    def __contains__(self, name: object) -> bool:
        return name in self._modules

    def names(self) -> list[str]:
        return list(self._modules)

    def specs(self) -> list[ModuleSpec]:
        return [rm.spec for rm in self._modules.values()]

    def source_of(self, name: str) -> str:
        return self._modules[name].source
