from __future__ import annotations

from importlib import resources
from pathlib import Path

import typer


def _template_text() -> str:
    return (resources.files("trustable") / "scaffold" / "trustable.yaml").read_text()


def register_init(app: typer.Typer) -> None:
    @app.command()
    def init(
        directory: Path = typer.Option(  # noqa: B008
            Path("."), "--dir", help="Target directory to scaffold into."
        ),
        force: bool = typer.Option(False, "--force", help="Overwrite an existing config."),
    ) -> None:
        """Scaffold a trustable.yaml and starter directories."""
        directory.mkdir(parents=True, exist_ok=True)
        config_path = directory / "trustable.yaml"
        if config_path.exists() and not force:
            typer.secho(
                f"{config_path} already exists (use --force to overwrite)",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        config_path.write_text(_template_text())
        for sub in ("prompts", "tests"):
            (directory / sub).mkdir(exist_ok=True)
        typer.secho(f"scaffolded {config_path} + prompts/ tests/", fg=typer.colors.GREEN)
