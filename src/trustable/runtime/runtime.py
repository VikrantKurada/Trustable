from __future__ import annotations

from trustable.config.schema import ModuleConfig, TrustableConfig
from trustable.plugins.registry import ModuleRegistry
from trustable.runtime.pipeline import Pipeline


class TrustableRuntime:
    def __init__(self, pipeline: Pipeline, modules: list[object]) -> None:
        self.pipeline = pipeline
        self.modules = modules

    @classmethod
    def from_config(
        cls,
        config: TrustableConfig,
        module_configs: dict[str, ModuleConfig],
        registry: ModuleRegistry,
    ) -> TrustableRuntime:
        ordered: list[tuple[int, object]] = []
        for name, module_config in module_configs.items():
            if not module_config.enabled or name not in registry:
                continue
            spec = registry.get(name)
            ordered.append((spec.priority, spec.factory(module_config)))
        ordered.sort(key=lambda item: item[0])
        modules = [instance for _, instance in ordered]
        return cls(pipeline=Pipeline(modules), modules=modules)
