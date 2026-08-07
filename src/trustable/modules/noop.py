from __future__ import annotations

import typer

from trustable.config.schema import ModuleConfig
from trustable.plugins.context import InteractionContext
from trustable.plugins.module import ModuleSpec


class NoopModule:
    """Reference module implementing every capability as a harmless pass-through."""

    def __init__(self, config: ModuleConfig | None) -> None:
        self.config = config

    def check_input(self, ctx: InteractionContext) -> None:
        ctx.metadata.setdefault("noop", []).append("input")

    def check_output(self, ctx: InteractionContext) -> None:
        ctx.metadata.setdefault("noop", []).append("output")

    def start_trace(self, ctx: InteractionContext) -> None:
        ctx.metadata["noop_trace"] = "started"

    def end_trace(self, ctx: InteractionContext) -> None:
        ctx.metadata["noop_trace"] = "ended"

    def register_cli(self, app: typer.Typer) -> None:
        @app.command("noop-ping")
        def _ping() -> None:
            """Reference command proving CommandProvider works."""
            typer.echo("pong")


def noop_spec() -> ModuleSpec:
    return ModuleSpec(
        name="noop", factory=lambda c: NoopModule(c), config_model=ModuleConfig, priority=50
    )
