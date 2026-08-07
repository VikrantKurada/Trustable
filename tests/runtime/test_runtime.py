from trustable.config.schema import ModuleConfig, TrustableConfig
from trustable.plugins.context import InteractionContext
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry
from trustable.runtime.runtime import TrustableRuntime


class Guard:
    def __init__(self, config):
        self.config = config

    def check_input(self, ctx):
        ctx.records.append({"guard": "ran"})


def _registry():
    reg = ModuleRegistry()
    reg.register(ModuleSpec("guard", lambda c: Guard(c), ModuleConfig, priority=10))
    reg.register(ModuleSpec("off", lambda c: Guard(c), ModuleConfig, priority=20))
    return reg


def test_only_enabled_modules_are_instantiated():
    config = TrustableConfig(project="x")
    module_configs = {
        "guard": ModuleConfig(enabled=True),
        "off": ModuleConfig(enabled=False),
    }
    rt = TrustableRuntime.from_config(config, module_configs, _registry())
    assert len(rt.modules) == 1
    ctx = InteractionContext(prompt="x")
    rt.pipeline.run_input_guards(ctx)
    assert ctx.records == [{"guard": "ran"}]
