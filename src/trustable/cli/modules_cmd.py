from __future__ import annotations

import typer

from trustable.config.errors import ConfigError
from trustable.config.loader import load_config
from trustable.config.schema import ModuleConfig, TrustableConfig
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


def _fresh_registry() -> tuple[ModuleRegistry, dict[str, ModuleConfig], list]:
    """Best-effort load the real project config for introspection.

    Falls back to a bare registry (no config, no module configs) when no usable
    `trustable.yaml` is found or it fails to load, so `modules list`/`info` still
    work outside a project directory.
    """
    registry = ModuleRegistry()
    try:
        loaded = load_config(None, registry)
    except ConfigError:
        registry = ModuleRegistry()
        errors = discover_modules(TrustableConfig(project="(introspection)"), registry)
        return registry, {}, errors
    return registry, loaded.module_configs, loaded.discovery_errors


def _enabled_state(name: str, module_configs: dict[str, ModuleConfig]) -> str:
    config = module_configs.get(name)
    if config is None:
        return "-"
    return "yes" if config.enabled else "no"


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
        """List discovered modules, their source, enabled state, and capabilities."""
        registry, module_configs, errors = _fresh_registry()
        for name in sorted(registry.names()):
            spec = registry.get(name)
            caps = ", ".join(_capabilities_of(spec)) or "(none)"
            enabled = _enabled_state(name, module_configs)
            typer.echo(
                f"{name:<16} source={registry.source_of(name):<11} enabled={enabled:<3} "
                f"priority={spec.priority:<4} capabilities=[{caps}]"
            )
        for err in errors:
            typer.secho(f"error   {err.ref} ({err.source}): {err.message}",
                        fg=typer.colors.RED, err=True)

    @modules_app.command("info")
    def info(name: str) -> None:
        """Show a module's config schema and capabilities."""
        registry, module_configs, _ = _fresh_registry()
        if name not in registry:
            typer.secho(f"unknown module '{name}'", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        spec = registry.get(name)
        enabled = _enabled_state(name, module_configs)
        typer.echo(f"module: {name}  (priority {spec.priority}, enabled={enabled})")
        typer.echo(f"capabilities: {', '.join(_capabilities_of(spec)) or '(none)'}")
        typer.echo("config fields:")
        for field_name, field in spec.config_model.model_fields.items():
            typer.echo(f"  {field_name}: {field.annotation} = {field.default!r}")

    app.add_typer(modules_app, name="modules")
