from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from trustable.plugins.context import InteractionContext

if TYPE_CHECKING:
    import typer


@runtime_checkable
class InputGuard(Protocol):
    def check_input(self, ctx: InteractionContext) -> None: ...


@runtime_checkable
class OutputGuard(Protocol):
    def check_output(self, ctx: InteractionContext) -> None: ...


@runtime_checkable
class Tracer(Protocol):
    def start_trace(self, ctx: InteractionContext) -> None: ...

    def end_trace(self, ctx: InteractionContext) -> None: ...


@runtime_checkable
class CommandProvider(Protocol):
    def register_cli(self, app: typer.Typer) -> None: ...
