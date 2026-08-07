from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from trustable.config.errors import (
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
    format_validation_error,
)
from trustable.config.schema import ModuleConfig, TrustableConfig
from trustable.plugins.discovery import DiscoveryError, discover_modules
from trustable.plugins.registry import ModuleRegistry


def find_config(start: Path | None = None, filename: str = "trustable.yaml") -> Path:
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    raise ConfigNotFoundError(f"no {filename} found from {current} upward")


def parse_envelope(path: Path) -> TrustableConfig:
    if not path.is_file():
        raise ConfigNotFoundError(f"config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigParseError(f"could not parse {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigValidationError(f"{path}: top level must be a mapping")
    try:
        return TrustableConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigValidationError(
            f"{path} is invalid:\n{format_validation_error(exc)}"
        ) from exc


def validate_modules(
    config: TrustableConfig, registry: ModuleRegistry
) -> dict[str, ModuleConfig]:
    typed: dict[str, ModuleConfig] = {}
    for name, raw in config.modules.items():
        if name not in registry:
            raise ConfigValidationError(
                f"unknown module '{name}' (not registered); "
                f"known modules: {', '.join(registry.names()) or '(none)'}"
            )
        model = registry.get(name).config_model
        try:
            typed[name] = model.model_validate(raw.model_dump())
        except ValidationError as exc:
            raise ConfigValidationError(
                f"module '{name}' config is invalid:\n{format_validation_error(exc)}"
            ) from exc
    return typed


@dataclass
class LoadedConfig:
    config: TrustableConfig
    module_configs: dict[str, ModuleConfig]
    discovery_errors: list[DiscoveryError]


def load_config(path: Path | None, registry: ModuleRegistry) -> LoadedConfig:
    resolved = path if path is not None else find_config()
    config = parse_envelope(resolved)
    discovery_errors = discover_modules(config, registry)
    module_configs = validate_modules(config, registry)
    return LoadedConfig(
        config=config, module_configs=module_configs, discovery_errors=discovery_errors
    )
