from pathlib import Path

import pytest

from trustable.config.errors import (
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
)
from trustable.config.loader import find_config, parse_envelope, validate_modules
from trustable.config.schema import AuditConfig, SecurityConfig
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry

PRD_YAML = """
version: "1.0"
project: "my-llm-app"
modules:
  security:
    enabled: true
    pii_masking: ["EMAIL", "API_KEYS"]
    block_injections: true
  audit:
    enabled: true
    sink: "databricks"
    log_level: "silver"
"""


def _registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(ModuleSpec("security", lambda c: object(), SecurityConfig, 10))
    reg.register(ModuleSpec("audit", lambda c: object(), AuditConfig, 30))
    return reg


def test_find_config_walks_up(tmp_path: Path):
    (tmp_path / "trustable.yaml").write_text("project: x")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_config(start=nested) == tmp_path / "trustable.yaml"


def test_find_config_missing_raises(tmp_path: Path):
    with pytest.raises(ConfigNotFoundError):
        find_config(start=tmp_path)


def test_parse_envelope_accepts_prd_yaml(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text(PRD_YAML)
    cfg = parse_envelope(p)
    assert cfg.project == "my-llm-app"
    assert cfg.modules["security"].enabled is True


def test_parse_envelope_bad_yaml_raises(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text("project: [unclosed")
    with pytest.raises(ConfigParseError):
        parse_envelope(p)


def test_parse_envelope_missing_project_raises(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text('version: "1.0"')
    with pytest.raises(ConfigValidationError):
        parse_envelope(p)


def test_validate_modules_accepts_prd(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text(PRD_YAML)
    cfg = parse_envelope(p)
    typed = validate_modules(cfg, _registry())
    assert isinstance(typed["security"], SecurityConfig)
    assert typed["security"].pii_masking == ["EMAIL", "API_KEYS"]


def test_validate_modules_unknown_module_raises(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text('project: x\nmodules:\n  frobnicate:\n    enabled: true\n')
    cfg = parse_envelope(p)
    with pytest.raises(ConfigValidationError) as exc:
        validate_modules(cfg, _registry())
    assert "frobnicate" in exc.value.message


def test_validate_modules_bad_field_raises(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text('project: x\nmodules:\n  security:\n    enabled: true\n    bogus: 1\n')
    cfg = parse_envelope(p)
    with pytest.raises(ConfigValidationError):
        validate_modules(cfg, _registry())
