from __future__ import annotations

import typer

from trustable.config.schema import TrustableConfig
from trustable.plugins.capabilities import (
    CommandProvider,
    InputGuard,
    OutputGuard,
    Tracer,
)
from trustable.plugins.discovery import discover_modules
from trustable.plugins.registry import ModuleRegistry

_CAPABILITIES = [
    ("InputGuard", InputGuard),
    ("OutputGuard", OutputGuard),
    ("Tracer", Tracer),
    ("CommandProvider", CommandProvider),
]


def _fresh_registry() -> tuple[ModuleRegistry, list]:
    registry = ModuleRegistry()
    errors = discover_modules(TrustableConfig(project="(introspection)"), registry)
    return registry, errors


def _capabilities_of(spec) -> list[str]:
    try:
        instance = spec.factory(spec.config_model())
    except Exception:  # noqa: BLE001 - introspection must not crash
        return []
    return [label for label, proto in _CAPABILITIES if isinstance(instance, proto)]


def register_modules(app: typer.Typer) -> None:
    modules_app = typer.Typer(help="Inspect discovered modules.", no_args_is_help=True)

    @modules_app.command("list")
    def list_() -> None:
        """List discovered modules, their source, and capabilities."""
        registry, errors = _fresh_registry()
        for name in sorted(registry.names()):
            spec = registry.get(name)
            caps = ", ".join(_capabilities_of(spec)) or "(none)"
            typer.echo(
                f"{name:<16} source={registry.source_of(name):<11} "
                f"priority={spec.priority:<4} capabilities=[{caps}]"
            )
        for err in errors:
            typer.secho(f"error   {err.ref} ({err.source}): {err.message}",
                        fg=typer.colors.RED, err=True)

    @modules_app.command("info")
    def info(name: str) -> None:
        """Show a module's config schema and capabilities."""
        registry, _ = _fresh_registry()
        if name not in registry:
            typer.secho(f"unknown module '{name}'", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        spec = registry.get(name)
        typer.echo(f"module: {name}  (priority {spec.priority})")
        typer.echo(f"capabilities: {', '.join(_capabilities_of(spec)) or '(none)'}")
        typer.echo("config fields:")
        for field_name, field in spec.config_model.model_fields.items():
            typer.echo(f"  {field_name}: {field.annotation} = {field.default!r}")

    app.add_typer(modules_app, name="modules")
