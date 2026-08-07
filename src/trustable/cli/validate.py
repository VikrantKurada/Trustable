from __future__ import annotations

from pathlib import Path

import typer

from trustable.config.errors import ConfigError
from trustable.config.loader import load_config
from trustable.plugins.registry import ModuleRegistry


def register_validate(app: typer.Typer) -> None:
    @app.command()
    def validate(
        path: Path | None = typer.Argument(  # noqa: B008
            None, help="Path to trustable.yaml (default: search upward from cwd)."
        ),
    ) -> None:
        """Validate a trustable.yaml configuration."""
        registry = ModuleRegistry()
        try:
            loaded = load_config(path, registry)
        except ConfigError as exc:
            typer.secho(exc.message, fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        for err in loaded.discovery_errors:
            typer.secho(
                f"warning: plugin '{err.ref}' ({err.source}) failed: {err.message}",
                fg=typer.colors.YELLOW,
                err=True,
            )

        enabled = [n for n, c in loaded.module_configs.items() if c.enabled]
        typer.secho(
            f"trustable.yaml is valid — project '{loaded.config.project}', "
            f"enabled modules: {', '.join(enabled) or '(none)'}",
            fg=typer.colors.GREEN,
        )
