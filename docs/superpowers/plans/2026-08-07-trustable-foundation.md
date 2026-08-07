# Trustable Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Trustable Foundation — a `trustable` Python package that parses/validates `trustable.yaml`, discovers modules from three sources, assembles a fail-open capability pipeline, and exposes it through a CLI.

**Architecture:** Capability-protocol plugin framework. Modules implement small typed `Protocol` capabilities (`InputGuard`, `OutputGuard`, `Tracer`, `CommandProvider`); a `TrustableRuntime` turns validated config into an ordered, fail-open middleware pipeline threading a single `InteractionContext` through each stage. Config uses a thin envelope (`TrustableConfig`) plus per-module two-pass validation driven by a registry.

**Tech Stack:** Python 3.11+, Typer (CLI), Pydantic v2 (config), PyYAML (parsing), pytest (tests), Ruff (lint/format), uv (env/deps), hatchling (build backend).

## Global Constraints

- Python **3.11+**. Single package **`trustable`**, `src/` layout, hatchling build backend.
- CLI = **Typer**; config validation = **Pydantic v2**; YAML parsing = **PyYAML** (`yaml.safe_load`).
- Config filename: **`trustable.yaml`**. Entry-point group: **`trustable.modules`**.
- `RawModuleConfig` uses **`extra="allow"`**; `ModuleConfig` base uses **`extra="forbid"`**.
- **Fail-loud at config-time** (non-zero exit, friendly message); **fail-open at runtime** (a throwing module is logged and skipped) — except an intentional `ctx.blocked` from a guard.
- Built-in module priorities (lower = earlier): **security 10, explainability 20, audit 30, noop 50, test 100**.
- Every task ends green (its tests pass) and with a commit. Run `ruff check .` before each commit.

---

## File Structure

```
trustable/
├── pyproject.toml
├── src/trustable/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py            # create_app(), build_app(), console entry-point
│   │   ├── validate.py        # `validate` command
│   │   ├── modules_cmd.py     # `modules list` / `modules info`
│   │   └── init_cmd.py        # `init` command
│   ├── config/
│   │   ├── __init__.py
│   │   ├── schema.py          # Pydantic models (envelope + module configs)
│   │   ├── errors.py          # ConfigError hierarchy + pydantic-error formatter
│   │   └── loader.py          # find_config, parse_envelope, validate_modules, load_config
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── context.py         # InteractionContext
│   │   ├── capabilities.py    # InputGuard / OutputGuard / Tracer / CommandProvider
│   │   ├── module.py          # ModuleSpec, ModuleFactory
│   │   ├── registry.py        # ModuleRegistry, RegisteredModule, DuplicateModuleError
│   │   └── discovery.py       # discover_modules, DiscoveryError
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── pipeline.py        # Pipeline
│   │   └── runtime.py         # TrustableRuntime
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── builtins.py        # stub specs + register_builtins()
│   │   └── noop.py            # NoopModule reference + noop_spec()
│   └── scaffold/
│       └── trustable.yaml     # template used by `init`
└── tests/                     # mirrors src/trustable/ layout
```

---

## Task 1: Project bootstrap & CLI skeleton

**Files:**
- Create: `pyproject.toml`, `src/trustable/__init__.py`, `src/trustable/cli/__init__.py`, `src/trustable/cli/main.py`
- Test: `tests/cli/test_version.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `trustable.__version__: str`; `trustable.cli.main.create_app() -> typer.Typer`; `trustable.cli.main.build_app() -> typer.Typer`; console script `trustable` → `trustable.cli.main:main`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "trustable"
version = "0.1.0"
description = "LLM quality & governance overlay"
requires-python = ">=3.11"
dependencies = ["typer>=0.12", "pydantic>=2.6", "pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.5"]

[project.scripts]
trustable = "trustable.cli.main:main"

# Third-party plugins advertise the "trustable.modules" entry-point group in their own
# pyproject; built-in modules are registered in code, so this package declares none.

[tool.hatch.build.targets.wheel]
packages = ["src/trustable"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `src/trustable/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Write the failing test** (`tests/cli/test_version.py`)

```python
from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()


def test_version_command_prints_version():
    result = runner.invoke(create_app(), ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_version_flag_prints_version():
    result = runner.invoke(create_app(), ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_version.py -v`
Expected: FAIL (`ModuleNotFoundError: trustable.cli.main`).

- [ ] **Step 5: Write `src/trustable/cli/__init__.py`** (empty file) **and `src/trustable/cli/main.py`**

```python
from __future__ import annotations

import sys

import typer

from trustable import __version__


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

    return app


def build_app() -> typer.Typer:
    """Core app plus best-effort dynamically-mounted module commands (see Task 12)."""
    return create_app()


def main() -> None:
    build_app()()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/cli/test_version.py -v`
Expected: PASS (both tests).

- [ ] **Step 7: Ruff + commit**

```bash
ruff check src tests && git add pyproject.toml src tests && \
git commit -m "feat: bootstrap trustable package and CLI skeleton with version"
```

---

## Task 2: InteractionContext

**Files:**
- Create: `src/trustable/plugins/__init__.py`, `src/trustable/plugins/context.py`
- Test: `tests/plugins/test_context.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `InteractionContext(prompt, response=None, metadata={}, records=[], blocked=False, block_reason=None)` dataclass.

- [ ] **Step 1: Write the failing test** (`tests/plugins/test_context.py`)

```python
from trustable.plugins.context import InteractionContext


def test_defaults_are_independent():
    a = InteractionContext(prompt="hi")
    b = InteractionContext(prompt="yo")
    a.metadata["k"] = 1
    a.records.append({"x": 1})
    assert b.metadata == {}  # no shared mutable default
    assert b.records == []
    assert a.response is None and a.blocked is False and a.block_reason is None


def test_fields_are_mutable():
    ctx = InteractionContext(prompt="hi")
    ctx.response = "answer"
    ctx.blocked = True
    ctx.block_reason = "injection"
    assert ctx.response == "answer"
    assert ctx.blocked and ctx.block_reason == "injection"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/plugins/test_context.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/plugins/__init__.py`** (empty) **and `src/trustable/plugins/context.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InteractionContext:
    """State threaded through the runtime pipeline for one LLM interaction."""

    prompt: Any
    response: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    records: list[dict[str, Any]] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/plugins/test_context.py -v`
Expected: PASS.

- [ ] **Step 5: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add InteractionContext"
```

---

## Task 3: Capability protocols

**Files:**
- Create: `src/trustable/plugins/capabilities.py`
- Test: `tests/plugins/test_capabilities.py`

**Interfaces:**
- Consumes: `InteractionContext` (Task 2).
- Produces: `@runtime_checkable` protocols `InputGuard.check_input(ctx)`, `OutputGuard.check_output(ctx)`, `Tracer.start_trace(ctx)`/`end_trace(ctx)`, `CommandProvider.register_cli(app)` — all returning `None`.

- [ ] **Step 1: Write the failing test** (`tests/plugins/test_capabilities.py`)

```python
from trustable.plugins.capabilities import (
    CommandProvider,
    InputGuard,
    OutputGuard,
    Tracer,
)
from trustable.plugins.context import InteractionContext


class OnlyInput:
    def check_input(self, ctx: InteractionContext) -> None:
        ctx.metadata["seen"] = True


def test_runtime_checkable_matches_only_implemented():
    obj = OnlyInput()
    assert isinstance(obj, InputGuard)
    assert not isinstance(obj, OutputGuard)
    assert not isinstance(obj, Tracer)
    assert not isinstance(obj, CommandProvider)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/plugins/test_capabilities.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/plugins/capabilities.py`**

```python
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
    def register_cli(self, app: "typer.Typer") -> None: ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/plugins/test_capabilities.py -v`
Expected: PASS.

> Note: `runtime_checkable` Protocols check method *presence*, not signatures. That is sufficient for pipeline dispatch here.

- [ ] **Step 5: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add capability protocols"
```

---

## Task 4: Config schema

**Files:**
- Create: `src/trustable/config/__init__.py`, `src/trustable/config/schema.py`
- Test: `tests/config/test_schema.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `PluginRef(ref)`, `RawModuleConfig(enabled=False, extra allow)`, `TrustableConfig(version, project, plugins, modules)`, `ModuleConfig(enabled=False, extra forbid)`, and `SecurityConfig`, `AuditConfig`, `TestConfig`, `ExplainabilityConfig`.

- [ ] **Step 1: Write the failing test** (`tests/config/test_schema.py`)

```python
import pytest
from pydantic import ValidationError

from trustable.config.schema import (
    AuditConfig,
    RawModuleConfig,
    SecurityConfig,
    TrustableConfig,
)


def test_envelope_requires_project():
    with pytest.raises(ValidationError):
        TrustableConfig()  # type: ignore[call-arg]


def test_raw_module_allows_extra_keys():
    raw = RawModuleConfig(enabled=True, pii_masking=["EMAIL"])  # type: ignore[call-arg]
    assert raw.enabled is True


def test_module_config_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        SecurityConfig(enabled=True, bogus=1)  # type: ignore[call-arg]


def test_audit_log_level_is_constrained():
    assert AuditConfig(enabled=True, log_level="silver").log_level == "silver"
    with pytest.raises(ValidationError):
        AuditConfig(enabled=True, log_level="platinum")  # type: ignore[arg-type]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/config/test_schema.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/config/__init__.py`** (empty) **and `src/trustable/config/schema.py`**

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class PluginRef(BaseModel):
    ref: str


class RawModuleConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    enabled: bool = False


class TrustableConfig(BaseModel):
    version: str = "1.0"
    project: str
    plugins: list[PluginRef] = []
    modules: dict[str, RawModuleConfig] = {}


class ModuleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False


class SecurityConfig(ModuleConfig):
    pii_masking: list[str] = []
    block_injections: bool = True


class AuditConfig(ModuleConfig):
    sink: str = "local"
    log_level: Literal["bronze", "silver", "gold"] = "silver"


class TestConfig(ModuleConfig):
    evaluator_model: str | None = None
    golden_dataset: str | None = None


class ExplainabilityConfig(ModuleConfig):
    capture_rag_context: bool = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/config/test_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add config schema models"
```

---

## Task 5: ModuleSpec & Registry

**Files:**
- Create: `src/trustable/plugins/module.py`, `src/trustable/plugins/registry.py`
- Test: `tests/plugins/test_registry.py`

**Interfaces:**
- Consumes: `ModuleConfig` (Task 4).
- Produces:
  - `ModuleFactory = Callable[[ModuleConfig], object]`
  - `ModuleSpec(name: str, factory: ModuleFactory, config_model: type[ModuleConfig], priority: int = 100)` (frozen dataclass)
  - `DuplicateModuleError(Exception)`
  - `ModuleRegistry` with `register(spec, source="builtin") -> None`, `get(name) -> ModuleSpec`, `__contains__(name) -> bool`, `names() -> list[str]`, `specs() -> list[ModuleSpec]`, `source_of(name) -> str`.

- [ ] **Step 1: Write the failing test** (`tests/plugins/test_registry.py`)

```python
import pytest

from trustable.config.schema import ModuleConfig
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import DuplicateModuleError, ModuleRegistry


def _spec(name: str, priority: int = 100) -> ModuleSpec:
    return ModuleSpec(
        name=name, factory=lambda c: object(), config_model=ModuleConfig, priority=priority
    )


def test_register_and_get():
    reg = ModuleRegistry()
    reg.register(_spec("audit"), source="builtin")
    assert "audit" in reg
    assert reg.get("audit").name == "audit"
    assert reg.source_of("audit") == "builtin"
    assert reg.names() == ["audit"]


def test_duplicate_registration_raises():
    reg = ModuleRegistry()
    reg.register(_spec("audit"))
    with pytest.raises(DuplicateModuleError):
        reg.register(_spec("audit"))


def test_get_unknown_raises_keyerror():
    reg = ModuleRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/plugins/test_registry.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/plugins/module.py`**

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from trustable.config.schema import ModuleConfig

ModuleFactory = Callable[[ModuleConfig], object]


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    factory: ModuleFactory
    config_model: type[ModuleConfig]
    priority: int = 100
```

- [ ] **Step 4: Write `src/trustable/plugins/registry.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from trustable.plugins.module import ModuleSpec


class DuplicateModuleError(Exception):
    """Raised when two modules register under the same name."""


@dataclass(frozen=True)
class RegisteredModule:
    spec: ModuleSpec
    source: str  # "builtin" | "entry_point" | "config"


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, RegisteredModule] = {}

    def register(self, spec: ModuleSpec, source: str = "builtin") -> None:
        if spec.name in self._modules:
            raise DuplicateModuleError(f"module '{spec.name}' is already registered")
        self._modules[spec.name] = RegisteredModule(spec=spec, source=source)

    def get(self, name: str) -> ModuleSpec:
        return self._modules[name].spec

    def __contains__(self, name: object) -> bool:
        return name in self._modules

    def names(self) -> list[str]:
        return list(self._modules)

    def specs(self) -> list[ModuleSpec]:
        return [rm.spec for rm in self._modules.values()]

    def source_of(self, name: str) -> str:
        return self._modules[name].source
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/plugins/test_registry.py -v`
Expected: PASS.

- [ ] **Step 6: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add ModuleSpec and ModuleRegistry"
```

---

## Task 6: Config loader (find, parse envelope, validate modules)

**Files:**
- Create: `src/trustable/config/errors.py`, `src/trustable/config/loader.py`
- Test: `tests/config/test_loader.py`

**Interfaces:**
- Consumes: `TrustableConfig`, `ModuleConfig` (Task 4); `ModuleRegistry` (Task 5).
- Produces:
  - `ConfigError(message)` base with `.message`; subclasses `ConfigNotFoundError`, `ConfigParseError`, `ConfigValidationError`.
  - `format_validation_error(exc) -> str` (turns a Pydantic `ValidationError` into a friendly multi-line string).
  - `find_config(start: Path | None = None, filename: str = "trustable.yaml") -> Path`
  - `parse_envelope(path: Path) -> TrustableConfig`
  - `validate_modules(config: TrustableConfig, registry: ModuleRegistry) -> dict[str, ModuleConfig]`

- [ ] **Step 1: Write the failing test** (`tests/config/test_loader.py`)

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/config/test_loader.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/config/errors.py`**

```python
from __future__ import annotations

from pydantic import ValidationError


class ConfigError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigNotFoundError(ConfigError):
    pass


class ConfigParseError(ConfigError):
    pass


class ConfigValidationError(ConfigError):
    pass


def format_validation_error(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(root)"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)
```

- [ ] **Step 4: Write `src/trustable/config/loader.py`**

```python
from __future__ import annotations

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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/config/test_loader.py -v`
Expected: PASS (all 8 tests).

- [ ] **Step 6: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add config loader with two-pass validation"
```

---

## Task 7: Built-in modules (stubs + noop reference)

**Files:**
- Create: `src/trustable/modules/__init__.py`, `src/trustable/modules/noop.py`, `src/trustable/modules/builtins.py`
- Test: `tests/modules/test_builtins.py`

**Interfaces:**
- Consumes: capability protocols (Task 3); `ModuleConfig` + module config models (Task 4); `ModuleSpec` (Task 5); `ModuleRegistry` (Task 5); `InteractionContext` (Task 2).
- Produces:
  - `NoopModule(config: ModuleConfig)` implementing all four capabilities.
  - `noop_spec() -> ModuleSpec` (name `"noop"`, priority 50, config_model `ModuleConfig`).
  - `register_builtins(registry: ModuleRegistry) -> None` registering security(10), explainability(20), audit(30), noop(50), test(100).

- [ ] **Step 1: Write the failing test** (`tests/modules/test_builtins.py`)

```python
import typer

from trustable.modules.builtins import register_builtins
from trustable.modules.noop import NoopModule
from trustable.plugins.capabilities import (
    CommandProvider,
    InputGuard,
    OutputGuard,
    Tracer,
)
from trustable.plugins.context import InteractionContext
from trustable.plugins.registry import ModuleRegistry


def test_noop_implements_all_capabilities():
    m = NoopModule(config=None)
    assert isinstance(m, InputGuard)
    assert isinstance(m, OutputGuard)
    assert isinstance(m, Tracer)
    assert isinstance(m, CommandProvider)


def test_noop_input_and_output_are_harmless():
    m = NoopModule(config=None)
    ctx = InteractionContext(prompt="hi")
    m.check_input(ctx)
    m.check_output(ctx)
    assert ctx.blocked is False
    assert ctx.metadata.get("noop") == ["input", "output"]


def test_noop_registers_a_cli_command():
    m = NoopModule(config=None)
    app = typer.Typer()
    m.register_cli(app)
    names = [c.name for c in app.registered_commands]
    assert "noop-ping" in names


def test_register_builtins_registers_all_five():
    reg = ModuleRegistry()
    register_builtins(reg)
    assert set(reg.names()) == {"security", "audit", "test", "explainability", "noop"}
    assert reg.get("security").priority == 10
    assert reg.get("noop").priority == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/modules/test_builtins.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/modules/__init__.py`** (empty) **and `src/trustable/modules/noop.py`**

```python
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
```

- [ ] **Step 4: Write `src/trustable/modules/builtins.py`**

```python
from __future__ import annotations

from trustable.config.schema import (
    AuditConfig,
    ExplainabilityConfig,
    ModuleConfig,
    SecurityConfig,
    TestConfig,
)
from trustable.modules.noop import noop_spec
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry


class _StubModule:
    """Placeholder for a module whose runtime behavior lands in a later sub-project.

    Implements no capabilities yet, so it contributes nothing to the pipeline.
    """

    def __init__(self, name: str, config: ModuleConfig) -> None:
        self.name = name
        self.config = config


def _stub_spec(name: str, config_model: type[ModuleConfig], priority: int) -> ModuleSpec:
    return ModuleSpec(
        name=name,
        factory=lambda c, _n=name: _StubModule(_n, c),
        config_model=config_model,
        priority=priority,
    )


def register_builtins(registry: ModuleRegistry) -> None:
    registry.register(_stub_spec("security", SecurityConfig, 10))
    registry.register(_stub_spec("explainability", ExplainabilityConfig, 20))
    registry.register(_stub_spec("audit", AuditConfig, 30))
    registry.register(noop_spec())
    registry.register(_stub_spec("test", TestConfig, 100))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/modules/test_builtins.py -v`
Expected: PASS.

- [ ] **Step 6: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add built-in module stubs and noop reference module"
```

---

## Task 8: Discovery & load_config orchestrator

**Files:**
- Create: `src/trustable/plugins/discovery.py`
- Modify: `src/trustable/config/loader.py` (append `LoadedConfig` + `load_config`)
- Test: `tests/plugins/test_discovery.py`, `tests/config/test_load_config.py`

**Interfaces:**
- Consumes: `TrustableConfig`, `PluginRef` (Task 4); `ModuleRegistry` (Task 5); `register_builtins` (Task 7); `find_config`, `parse_envelope`, `validate_modules` (Task 6).
- Produces:
  - `DiscoveryError(source: str, ref: str, message: str)` dataclass.
  - `discover_modules(config: TrustableConfig, registry: ModuleRegistry) -> list[DiscoveryError]` — registers built-ins, then `trustable.modules` entry-points (`source="entry_point"`), then `config.plugins` refs (`source="config"`). A ref resolves via `"pkg.mod:attr"`; the target is a `ModuleSpec` or a zero-arg callable returning one. Import/type failures become `DiscoveryError` rows (never raised).
  - `LoadedConfig(config, module_configs, discovery_errors)` dataclass and `load_config(path: Path | None, registry: ModuleRegistry) -> LoadedConfig` in `loader.py`.

- [ ] **Step 1: Write the failing test** (`tests/plugins/test_discovery.py`)

```python
from pathlib import Path

from trustable.config.schema import PluginRef, TrustableConfig
from trustable.plugins.discovery import discover_modules
from trustable.plugins.registry import ModuleRegistry

_PLUGIN_SRC = """
from trustable.plugins.module import ModuleSpec
from trustable.config.schema import ModuleConfig


def provider():
    return ModuleSpec("custom", lambda c: object(), ModuleConfig, 200)
"""


def test_discovers_builtins():
    reg = ModuleRegistry()
    errors = discover_modules(TrustableConfig(project="x"), reg)
    assert errors == []
    assert "security" in reg and "noop" in reg


def test_discovers_config_plugin_ref(tmp_path: Path, monkeypatch):
    (tmp_path / "myplugin.py").write_text(_PLUGIN_SRC)
    monkeypatch.syspath_prepend(str(tmp_path))
    reg = ModuleRegistry()
    cfg = TrustableConfig(project="x", plugins=[PluginRef(ref="myplugin:provider")])
    errors = discover_modules(cfg, reg)
    assert errors == []
    assert "custom" in reg
    assert reg.source_of("custom") == "config"


def test_broken_plugin_ref_becomes_error_row():
    reg = ModuleRegistry()
    cfg = TrustableConfig(project="x", plugins=[PluginRef(ref="does.not:exist")])
    errors = discover_modules(cfg, reg)
    assert len(errors) == 1
    assert errors[0].source == "config"
    assert "does.not:exist" in errors[0].ref
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/plugins/test_discovery.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/plugins/discovery.py`**

```python
from __future__ import annotations

import importlib
from dataclasses import dataclass
from importlib import metadata

from trustable.config.schema import TrustableConfig
from trustable.modules.builtins import register_builtins
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry

ENTRY_POINT_GROUP = "trustable.modules"


@dataclass
class DiscoveryError:
    source: str  # "entry_point" | "config"
    ref: str
    message: str


def _resolve_ref(ref: str) -> object:
    module_path, _, attr = ref.partition(":")
    if not attr:
        raise ValueError(f"plugin ref must be 'module:attr', got '{ref}'")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def _coerce_spec(target: object) -> ModuleSpec:
    obj = target() if callable(target) and not isinstance(target, ModuleSpec) else target
    if not isinstance(obj, ModuleSpec):
        raise TypeError("plugin did not resolve to a ModuleSpec")
    return obj


def discover_modules(
    config: TrustableConfig, registry: ModuleRegistry
) -> list[DiscoveryError]:
    errors: list[DiscoveryError] = []

    register_builtins(registry)

    for ep in metadata.entry_points(group=ENTRY_POINT_GROUP):
        try:
            registry.register(_coerce_spec(ep.load()), source="entry_point")
        except Exception as exc:  # noqa: BLE001 - discovery must be resilient
            errors.append(DiscoveryError("entry_point", ep.value, str(exc)))

    for plugin in config.plugins:
        try:
            registry.register(_coerce_spec(_resolve_ref(plugin.ref)), source="config")
        except Exception as exc:  # noqa: BLE001 - discovery must be resilient
            errors.append(DiscoveryError("config", plugin.ref, str(exc)))

    return errors
```

- [ ] **Step 4: Run discovery tests to verify they pass**

Run: `python -m pytest tests/plugins/test_discovery.py -v`
Expected: PASS.

- [ ] **Step 5: Append `LoadedConfig` + `load_config` to `src/trustable/config/loader.py`**

Add these imports at the top of `loader.py` (merge with existing imports):

```python
from dataclasses import dataclass

from trustable.plugins.discovery import DiscoveryError, discover_modules
```

Append to the end of `loader.py`:

```python
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
```

- [ ] **Step 6: Write the failing test** (`tests/config/test_load_config.py`)

```python
from pathlib import Path

from trustable.config.loader import load_config
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


def test_load_config_full_flow(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text(PRD_YAML)
    loaded = load_config(p, ModuleRegistry())
    assert loaded.config.project == "my-llm-app"
    assert loaded.module_configs["security"].enabled is True
    assert loaded.discovery_errors == []
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/config/test_load_config.py tests/plugins/test_discovery.py -v`
Expected: PASS.

- [ ] **Step 8: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add three-source discovery and load_config orchestrator"
```

---

## Task 9: Runtime & Pipeline

**Files:**
- Create: `src/trustable/runtime/__init__.py`, `src/trustable/runtime/pipeline.py`, `src/trustable/runtime/runtime.py`
- Test: `tests/runtime/test_pipeline.py`, `tests/runtime/test_runtime.py`

**Interfaces:**
- Consumes: capability protocols (Task 3); `InteractionContext` (Task 2); `TrustableConfig` + `ModuleConfig` (Task 4); `ModuleRegistry` (Task 5).
- Produces:
  - `Pipeline(modules: list[object])` with `run_input_guards(ctx) -> None`, `run_output_guards(ctx) -> None`, and `trace(ctx)` (a context manager). Each module call is fail-open (logged & skipped on exception); `run_input_guards` stops early once `ctx.blocked` is set.
  - `TrustableRuntime(pipeline: Pipeline, modules: list[object])` and classmethod `from_config(config: TrustableConfig, module_configs: dict[str, ModuleConfig], registry: ModuleRegistry) -> TrustableRuntime` — instantiates enabled modules via their factory, sorted by `spec.priority`.

- [ ] **Step 1: Write the failing test** (`tests/runtime/test_pipeline.py`)

```python
import pytest

from trustable.plugins.context import InteractionContext
from trustable.runtime.pipeline import Pipeline


class RecordingInput:
    def __init__(self, tag, block=False):
        self.tag, self.block = tag, block

    def check_input(self, ctx):
        ctx.records.append({"in": self.tag})
        if self.block:
            ctx.blocked = True
            ctx.block_reason = self.tag


class ThrowingInput:
    def check_input(self, ctx):
        raise RuntimeError("boom")


class RecordingTracer:
    def start_trace(self, ctx):
        ctx.records.append({"trace": "start"})

    def end_trace(self, ctx):
        ctx.records.append({"trace": "end"})


def test_input_guards_run_in_given_order():
    ctx = InteractionContext(prompt="x")
    Pipeline([RecordingInput("a"), RecordingInput("b")]).run_input_guards(ctx)
    assert ctx.records == [{"in": "a"}, {"in": "b"}]


def test_blocked_short_circuits_remaining_guards():
    ctx = InteractionContext(prompt="x")
    Pipeline([RecordingInput("a", block=True), RecordingInput("b")]).run_input_guards(ctx)
    assert ctx.blocked is True and ctx.block_reason == "a"
    assert ctx.records == [{"in": "a"}]  # "b" never ran


def test_throwing_module_is_failed_open():
    ctx = InteractionContext(prompt="x")
    Pipeline([ThrowingInput(), RecordingInput("b")]).run_input_guards(ctx)
    assert ctx.records == [{"in": "b"}]  # pipeline survived the exception


def test_trace_context_manager_wraps():
    ctx = InteractionContext(prompt="x")
    pipe = Pipeline([RecordingTracer()])
    with pipe.trace(ctx):
        ctx.records.append({"call": "llm"})
    assert ctx.records == [{"trace": "start"}, {"call": "llm"}, {"trace": "end"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/runtime/test_pipeline.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/runtime/__init__.py`** (empty) **and `src/trustable/runtime/pipeline.py`**

```python
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from trustable.plugins.capabilities import InputGuard, OutputGuard, Tracer
from trustable.plugins.context import InteractionContext

logger = logging.getLogger("trustable.runtime")


class Pipeline:
    def __init__(self, modules: list[object]) -> None:
        self._input_guards = [m for m in modules if isinstance(m, InputGuard)]
        self._output_guards = [m for m in modules if isinstance(m, OutputGuard)]
        self._tracers = [m for m in modules if isinstance(m, Tracer)]

    def run_input_guards(self, ctx: InteractionContext) -> None:
        for guard in self._input_guards:
            if ctx.blocked:
                return
            try:
                guard.check_input(ctx)
            except Exception:  # noqa: BLE001 - fail open
                logger.exception("input guard %r failed; skipping", guard)

    def run_output_guards(self, ctx: InteractionContext) -> None:
        for guard in self._output_guards:
            try:
                guard.check_output(ctx)
            except Exception:  # noqa: BLE001 - fail open
                logger.exception("output guard %r failed; skipping", guard)

    @contextmanager
    def trace(self, ctx: InteractionContext) -> Iterator[InteractionContext]:
        for tracer in self._tracers:
            try:
                tracer.start_trace(ctx)
            except Exception:  # noqa: BLE001 - fail open
                logger.exception("tracer %r start failed; skipping", tracer)
        try:
            yield ctx
        finally:
            for tracer in reversed(self._tracers):
                try:
                    tracer.end_trace(ctx)
                except Exception:  # noqa: BLE001 - fail open
                    logger.exception("tracer %r end failed; skipping", tracer)
```

- [ ] **Step 4: Run pipeline tests to verify they pass**

Run: `python -m pytest tests/runtime/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Write the failing test** (`tests/runtime/test_runtime.py`)

```python
from trustable.config.schema import ModuleConfig, TrustableConfig
from trustable.plugins.context import InteractionContext
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry
from trustable.runtime.runtime import TrustableRuntime


class Guard:
    def __init__(self, config):
        self.config = config

    def check_input(self, ctx):
        ctx.records.append({"guard": "ran"})


def _registry():
    reg = ModuleRegistry()
    reg.register(ModuleSpec("guard", lambda c: Guard(c), ModuleConfig, priority=10))
    reg.register(ModuleSpec("off", lambda c: Guard(c), ModuleConfig, priority=20))
    return reg


def test_only_enabled_modules_are_instantiated():
    config = TrustableConfig(project="x")
    module_configs = {
        "guard": ModuleConfig(enabled=True),
        "off": ModuleConfig(enabled=False),
    }
    rt = TrustableRuntime.from_config(config, module_configs, _registry())
    assert len(rt.modules) == 1
    ctx = InteractionContext(prompt="x")
    rt.pipeline.run_input_guards(ctx)
    assert ctx.records == [{"guard": "ran"}]
```

- [ ] **Step 6: Write `src/trustable/runtime/runtime.py`**

```python
from __future__ import annotations

from trustable.config.schema import ModuleConfig, TrustableConfig
from trustable.plugins.registry import ModuleRegistry
from trustable.runtime.pipeline import Pipeline


class TrustableRuntime:
    def __init__(self, pipeline: Pipeline, modules: list[object]) -> None:
        self.pipeline = pipeline
        self.modules = modules

    @classmethod
    def from_config(
        cls,
        config: TrustableConfig,
        module_configs: dict[str, ModuleConfig],
        registry: ModuleRegistry,
    ) -> "TrustableRuntime":
        ordered: list[tuple[int, object]] = []
        for name, module_config in module_configs.items():
            if not module_config.enabled or name not in registry:
                continue
            spec = registry.get(name)
            ordered.append((spec.priority, spec.factory(module_config)))
        ordered.sort(key=lambda item: item[0])
        modules = [instance for _, instance in ordered]
        return cls(pipeline=Pipeline(modules), modules=modules)
```

- [ ] **Step 7: Run runtime tests to verify they pass**

Run: `python -m pytest tests/runtime/ -v`
Expected: PASS.

- [ ] **Step 8: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add fail-open runtime pipeline and TrustableRuntime"
```

---

## Task 10: CLI `validate`

**Files:**
- Create: `src/trustable/cli/validate.py`
- Modify: `src/trustable/cli/main.py` (register `validate` in `create_app`)
- Test: `tests/cli/test_validate.py`

**Interfaces:**
- Consumes: `load_config`, `LoadedConfig`, `ConfigError` (Tasks 6/8); `ModuleRegistry` (Task 5).
- Produces: `validate` command; `register_validate(app: typer.Typer) -> None`.

- [ ] **Step 1: Write the failing test** (`tests/cli/test_validate.py`)

```python
from pathlib import Path

from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()

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


def test_validate_accepts_prd_yaml(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text(PRD_YAML)
    result = runner.invoke(create_app(), ["validate", str(p)])
    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_validate_rejects_bad_log_level(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text('project: x\nmodules:\n  audit:\n    enabled: true\n    log_level: platinum\n')
    result = runner.invoke(create_app(), ["validate", str(p)])
    assert result.exit_code == 1
    assert "audit" in result.output


def test_validate_missing_file(tmp_path: Path):
    result = runner.invoke(create_app(), ["validate", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_validate.py -v`
Expected: FAIL (no `validate` command → non-zero, but not for the asserted reasons).

- [ ] **Step 3: Write `src/trustable/cli/validate.py`**

```python
from __future__ import annotations

from pathlib import Path

import typer

from trustable.config.errors import ConfigError
from trustable.config.loader import load_config
from trustable.plugins.registry import ModuleRegistry


def register_validate(app: typer.Typer) -> None:
    @app.command()
    def validate(
        path: Path | None = typer.Argument(
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
```

- [ ] **Step 4: Register `validate` in `create_app`** (`src/trustable/cli/main.py`)

Add the import near the top and call it inside `create_app` before `return app`:

```python
from trustable.cli.validate import register_validate
```
```python
    register_validate(app)
    return app
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/cli/test_validate.py -v`
Expected: PASS.

- [ ] **Step 6: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add trustable validate command"
```

---

## Task 11: CLI `modules list` / `modules info`

**Files:**
- Create: `src/trustable/cli/modules_cmd.py`
- Modify: `src/trustable/cli/main.py` (register the `modules` sub-app)
- Test: `tests/cli/test_modules_cmd.py`

**Interfaces:**
- Consumes: `discover_modules` (Task 8); `ModuleRegistry` (Task 5); capability protocols (Task 3); config models (Task 4); `find_config`/`parse_envelope`/`ConfigError` (Task 6).
- Produces: a `modules` Typer sub-app with `list` and `info <name>`; `register_modules(app: typer.Typer) -> None`. Capabilities are derived by instantiating each spec with `spec.config_model()` and `isinstance`-checking the four protocols.

- [ ] **Step 1: Write the failing test** (`tests/cli/test_modules_cmd.py`)

```python
from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()


def test_modules_list_shows_builtins():
    result = runner.invoke(create_app(), ["modules", "list"])
    assert result.exit_code == 0
    for name in ("security", "audit", "test", "explainability", "noop"):
        assert name in result.output


def test_modules_list_marks_noop_capabilities():
    result = runner.invoke(create_app(), ["modules", "list"])
    assert "InputGuard" in result.output  # noop advertises capabilities


def test_modules_info_shows_schema_fields():
    result = runner.invoke(create_app(), ["modules", "info", "audit"])
    assert result.exit_code == 0
    assert "log_level" in result.output
    assert "sink" in result.output


def test_modules_info_unknown_exits_nonzero():
    result = runner.invoke(create_app(), ["modules", "info", "nope"])
    assert result.exit_code == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_modules_cmd.py -v`
Expected: FAIL (no `modules` command).

- [ ] **Step 3: Write `src/trustable/cli/modules_cmd.py`**

```python
from __future__ import annotations

import typer

from trustable.plugins.capabilities import (
    CommandProvider,
    InputGuard,
    OutputGuard,
    Tracer,
)
from trustable.plugins.discovery import discover_modules
from trustable.plugins.registry import ModuleRegistry
from trustable.config.schema import TrustableConfig

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
```

- [ ] **Step 4: Register the `modules` sub-app in `create_app`** (`src/trustable/cli/main.py`)

```python
from trustable.cli.modules_cmd import register_modules
```
```python
    register_modules(app)
    return app
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/cli/test_modules_cmd.py -v`
Expected: PASS.

- [ ] **Step 6: Ruff + commit**

```bash
ruff check src tests && git add src tests && \
git commit -m "feat: add trustable modules list/info commands"
```

---

## Task 12: CLI `init`, scaffold template & module-command mounting

**Files:**
- Create: `src/trustable/cli/init_cmd.py`, `src/trustable/scaffold/trustable.yaml`
- Modify: `src/trustable/cli/main.py` (register `init`; implement `build_app` mounting), `pyproject.toml` (include scaffold data in the wheel)
- Test: `tests/cli/test_init_cmd.py`, `tests/cli/test_mounting.py`

**Interfaces:**
- Consumes: `load_config` (Task 8); `CommandProvider` (Task 3); `ModuleRegistry` (Task 5); `create_app` (Task 1).
- Produces: `init` command; `register_init(app) -> None`; `build_app()` now best-effort mounts enabled `CommandProvider` module commands.

- [ ] **Step 1: Write the scaffold template** (`src/trustable/scaffold/trustable.yaml`)

```yaml
version: "1.0"
project: "my-llm-app"

modules:
  security:
    enabled: false
    pii_masking: ["EMAIL", "API_KEYS"]
    block_injections: true

  audit:
    enabled: false
    sink: "local"
    log_level: "silver"

  test:
    enabled: false
    evaluator_model: "ollama/llama3"
    golden_dataset: "./tests/golden_data.json"

  explainability:
    enabled: false
    capture_rag_context: true
```

- [ ] **Step 2: Ensure scaffold ships in the wheel** — add to `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.force-include]
"src/trustable/scaffold" = "trustable/scaffold"
```

- [ ] **Step 3: Write the failing test** (`tests/cli/test_init_cmd.py`)

```python
from pathlib import Path

from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()


def test_init_scaffolds_config_and_dirs(tmp_path: Path):
    result = runner.invoke(create_app(), ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "trustable.yaml").is_file()
    assert (tmp_path / "prompts").is_dir()
    assert (tmp_path / "tests").is_dir()
    assert "my-llm-app" in (tmp_path / "trustable.yaml").read_text()


def test_init_refuses_overwrite_without_force(tmp_path: Path):
    (tmp_path / "trustable.yaml").write_text("existing")
    result = runner.invoke(create_app(), ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 1
    assert (tmp_path / "trustable.yaml").read_text() == "existing"


def test_init_force_overwrites(tmp_path: Path):
    (tmp_path / "trustable.yaml").write_text("existing")
    result = runner.invoke(create_app(), ["init", "--dir", str(tmp_path), "--force"])
    assert result.exit_code == 0
    assert "my-llm-app" in (tmp_path / "trustable.yaml").read_text()
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_init_cmd.py -v`
Expected: FAIL (no `init` command).

- [ ] **Step 5: Write `src/trustable/cli/init_cmd.py`**

```python
from __future__ import annotations

import importlib.resources as resources
from pathlib import Path

import typer


def _template_text() -> str:
    return (resources.files("trustable") / "scaffold" / "trustable.yaml").read_text()


def register_init(app: typer.Typer) -> None:
    @app.command()
    def init(
        directory: Path = typer.Option(
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
```

- [ ] **Step 6: Register `init` in `create_app`** (`src/trustable/cli/main.py`)

```python
from trustable.cli.init_cmd import register_init
```
```python
    register_init(app)
    return app
```

- [ ] **Step 7: Run init tests to verify they pass**

Run: `python -m pytest tests/cli/test_init_cmd.py -v`
Expected: PASS.

- [ ] **Step 8: Write the failing test for module-command mounting** (`tests/cli/test_mounting.py`)

```python
from pathlib import Path

from typer.testing import CliRunner

from trustable.cli.main import build_app

runner = CliRunner()

CONFIG_WITH_NOOP = 'project: x\nmodules:\n  noop:\n    enabled: true\n'


def test_enabled_command_provider_is_mounted(tmp_path: Path, monkeypatch):
    (tmp_path / "trustable.yaml").write_text(CONFIG_WITH_NOOP)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(build_app(), ["noop-ping"])
    assert result.exit_code == 0
    assert "pong" in result.output


def test_build_app_survives_missing_config(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no trustable.yaml present
    result = runner.invoke(build_app(), ["version"])
    assert result.exit_code == 0  # core commands still work
```

- [ ] **Step 9: Implement mounting in `build_app`** (`src/trustable/cli/main.py`)

Replace the placeholder `build_app` from Task 1 with:

```python
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
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `python -m pytest tests/cli/test_mounting.py tests/cli/test_init_cmd.py -v`
Expected: PASS.

- [ ] **Step 11: Full suite + ruff + commit**

```bash
python -m pytest -q && ruff check src tests && git add src tests pyproject.toml && \
git commit -m "feat: add trustable init and dynamic module-command mounting"
```

---

## Final verification

- [ ] **Install & smoke-test the CLI end to end**

```bash
pip install -e ".[dev]"
python -m pytest -q
trustable version
cd "$(mktemp -d)" && trustable init && trustable validate && trustable modules list && trustable noop-ping
```

Expected: full suite green; `init` scaffolds; `validate` reports the config valid; `modules list` shows five built-ins with `noop` advertising four capabilities; `noop-ping` prints `pong`.

---

## Acceptance criteria coverage (self-review)

1. `pip install -e .` exposes a working CLI → Task 1 + Final verification.
2. `init` scaffolds; re-run without `--force` refused → Task 12.
3. `validate` accepts PRD yaml, rejects malformed with friendly errors + non-zero exit → Tasks 6, 10.
4. `modules list` shows built-ins + reference, enabled state/capabilities/source; broken plugin as error row → Tasks 7, 8, 11.
5. `modules info security` prints config schema → Task 11.
6. `TrustableRuntime.from_config` assembles ordered pipeline; guards run in priority order; `blocked` short-circuits; throwing module skipped → Task 9.
7. Noop reference module round-trips through the pipeline → Tasks 7, 9 (+ mounting proof in 12).
8. Full test suite passes; Ruff clean → every task + Final verification.
