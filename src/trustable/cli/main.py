from __future__ import annotations

import sys

import typer

from trustable import __version__
from trustable.cli.modules_cmd import register_modules
from trustable.cli.validate import register_validate


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"trustable {__version__} (Python {sys.version.split()[0]})")
        raise typer.Exit()


def create_app() -> typer.Typer:
    """Assemble the core CLI app (no dynamic module commands)."""
    app = typer.Typer(help="Trustable — LLM quality & governance overlay", no_args_is_help=True)

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
        typer.echo(f"trustable {__version__} (Python {sys.version.split()[0]})")

    register_validate(app)
    register_modules(app)
    return app


def build_app() -> typer.Typer:
    """Core app plus best-effort dynamically-mounted module commands (see Task 12)."""
    return create_app()


def main() -> None:
    build_app()()
