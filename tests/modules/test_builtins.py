import typer

from trustable.modules.builtins import register_builtins
from trustable.modules.noop import NoopModule
from trustable.plugins.capabilities import (
    CommandProvider,
    InputGuard,
    OutputGuard,
    Tracer,
)
from trustable.plugins.context import InteractionContext
from trustable.plugins.registry import ModuleRegistry


def test_noop_implements_all_capabilities():
    m = NoopModule(config=None)
    assert isinstance(m, InputGuard)
    assert isinstance(m, OutputGuard)
    assert isinstance(m, Tracer)
    assert isinstance(m, CommandProvider)


def test_noop_input_and_output_are_harmless():
    m = NoopModule(config=None)
    ctx = InteractionContext(prompt="hi")
    m.check_input(ctx)
    m.check_output(ctx)
    assert ctx.blocked is False
    assert ctx.metadata.get("noop") == ["input", "output"]


def test_noop_registers_a_cli_command():
    m = NoopModule(config=None)
    app = typer.Typer()
    m.register_cli(app)
    names = [c.name for c in app.registered_commands]
    assert "noop-ping" in names


def test_register_builtins_registers_all_five():
    reg = ModuleRegistry()
    register_builtins(reg)
    assert set(reg.names()) == {"security", "audit", "test", "explainability", "noop"}
    assert reg.get("security").priority == 10
    assert reg.get("noop").priority == 50
