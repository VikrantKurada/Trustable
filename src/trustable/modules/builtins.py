from __future__ import annotations

from trustable.config.schema import (
    AuditConfig,
    ExplainabilityConfig,
    ModuleConfig,
    SecurityConfig,
    TestConfig,
)
from trustable.modules.noop import noop_spec
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry


class _StubModule:
    """Placeholder for a module whose runtime behavior lands in a later sub-project.

    Implements no capabilities yet, so it contributes nothing to the pipeline.
    """

    def __init__(self, name: str, config: ModuleConfig) -> None:
        self.name = name
        self.config = config


def _stub_spec(name: str, config_model: type[ModuleConfig], priority: int) -> ModuleSpec:
    return ModuleSpec(
        name=name,
        factory=lambda c, _n=name: _StubModule(_n, c),
        config_model=config_model,
        priority=priority,
    )


def register_builtins(registry: ModuleRegistry) -> None:
    registry.register(_stub_spec("security", SecurityConfig, 10))
    registry.register(_stub_spec("explainability", ExplainabilityConfig, 20))
    registry.register(_stub_spec("audit", AuditConfig, 30))
    registry.register(noop_spec())
    registry.register(_stub_spec("test", TestConfig, 100))
