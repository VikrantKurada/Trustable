from __future__ import annotations

import sys

import typer

from trustable import __version__
from trustable.cli.init_cmd import register_init
from trustable.cli.modules_cmd import register_modules
from trustable.cli.validate import register_validate


def _version_string() -> str:
    return f"trustable {__version__} (Python {sys.version.split()[0]})"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(_version_string())
        raise typer.Exit()


def create_app() -> typer.Typer:
    """Assemble the core CLI app (no dynamic module commands)."""
    app = typer.Typer(help="Trustable - LLM quality & governance overlay", no_args_is_help=True)

    @app.callback()
    def _root(
        version: bool = typer.Option(
            False, "--version", callback=_version_callback, is_eager=True, help="Show version."
        ),
    ) -> None:
        pass

    @app.command()
    def version() -> None:
        """Print version information."""
        typer.echo(_version_string())

    register_validate(app)
    register_modules(app)
    register_init(app)
    return app


def build_app() -> typer.Typer:
    """Core app plus best-effort dynamically-mounted enabled module commands."""
    from trustable.config.loader import load_config
    from trustable.plugins.capabilities import CommandProvider
    from trustable.plugins.registry import ModuleRegistry
    from trustable.runtime.runtime import TrustableRuntime

    app = create_app()
    try:
        registry = ModuleRegistry()
        loaded = load_config(None, registry)
        runtime = TrustableRuntime.from_config(
            loaded.config, loaded.module_configs, registry
        )
        for module in runtime.modules:
            if isinstance(module, CommandProvider):
                module.register_cli(app)
    except Exception:  # noqa: BLE001 - never let mounting break core commands
        pass
    return app


def main() -> None:
    build_app()()
