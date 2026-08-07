from trustable.plugins.capabilities import (
    CommandProvider,
    InputGuard,
    OutputGuard,
    Tracer,
)
from trustable.plugins.context import InteractionContext


class OnlyInput:
    def check_input(self, ctx: InteractionContext) -> None:
        ctx.metadata["seen"] = True


def test_runtime_checkable_matches_only_implemented():
    obj = OnlyInput()
    assert isinstance(obj, InputGuard)
    assert not isinstance(obj, OutputGuard)
    assert not isinstance(obj, Tracer)
    assert not isinstance(obj, CommandProvider)
