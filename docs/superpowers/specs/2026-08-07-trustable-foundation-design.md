# Trustable — Foundation (Sub-project #1) Design

**Date:** 2026-08-07
**Status:** Approved (design), pending implementation plan
**Source PRD:** [`Trustable_PRD_v1.md`](../../../Trustable_PRD_v1.md)

---

## 1. Context

**Trustable** is a modular LLM quality & governance overlay: a configurable middle layer
(guardrails) dropped onto existing early-stage LLM projects via a `trustable.yaml` file plus a
Python SDK/CLI. It enforces security, reviewability, testability, auditability, and
explainability without rewriting the host application.

The full PRD spans **five feature modules plus a CLI/SDK/config foundation and CI/CD tooling** —
too large for one spec. It is decomposed into sub-projects, each with its own design → plan →
implementation cycle:

| # | Sub-project | Covers | PRD phase |
|---|---|---|---|
| **1** | **Foundation** *(this spec)* | `trustable.yaml` schema + parser, CLI skeleton, plugin/module framework, runtime pipeline assembly | Phase 1 |
| 2 | SDK: Audit & Explainability | `@trustable.trace`, OpenTelemetry capture, RAG-context + CoT logging, Bronze/Silver/Gold sinks | Phase 2 |
| 3 | Testing Harness | Golden-dataset runner, LLM-as-a-judge, YAML assertions, `trustable test` | Phase 3 |
| 4 | Security Module | PII/secret masking, prompt-injection scanning | woven in |
| 5 | Reviewability | Prompts-as-code registry, GitHub Action semantic diffing | woven in |
| 6 | Integrations & CI/CD | Dockerfile, GitHub Actions, enterprise sinks (Databricks/Unity Catalog) | Phase 4 |

This spec covers **sub-project #1 only.**

### Decisions locked in during brainstorming

- **Build intent:** Foundation for a **real product** (solid architecture, real integrations added
  incrementally; ruthless YAGNI on speculative machinery).
- **Plugin scope:** Build the **full plugin framework now** — Module interface, registry, dynamic
  discovery via entry-points, and config-declared plugins. (Still disciplined about *which* hook
  types exist: only those the PRD's real modules need.)
- **Architecture:** **Capability protocols + middleware pipeline** (typed capability interfaces;
  modules composed into an ordered pipeline around each interaction).
- **Stack:** Python 3.11+, single pip-installable package `trustable` (CLI + SDK together),
  **Typer** (CLI), **Pydantic v2** (config schema/validation), **PyYAML** (parsing),
  **pytest** (tests), **Ruff** (lint/format), **uv** (env/deps), **hatchling** (build backend).

---

## 2. Goals & non-goals

**Goals (this sub-project delivers):**
- Parse and validate the exact `trustable.yaml` from the PRD, with precise, friendly errors.
- A plugin framework: typed capability protocols, a module registry, three-source discovery
  (built-ins, entry-points, config `plugins:`), and per-module config validation.
- Runtime assembly: a `TrustableRuntime` that turns config → an ordered, fail-open capability
  pipeline, with an engine API (`run_input_guards`, `run_output_guards`, `trace`).
- A CLI: `init`, `validate`, `modules list`, `modules info`, `version`.
- A working **reference module** implementing all capabilities, proving the framework end-to-end.
- Comprehensive tests.

**Non-goals (deferred to later sub-projects):**
- The developer-facing SDK wrapper that intercepts live LLM calls (`@trustable.trace`,
  auto-instrumentation) — sub-project #2.
- Real behavior for security/audit/test/explainability modules — later sub-projects. Here they are
  **registered with real config models + stub factories** so `validate` is meaningful today.
- Any enterprise sink, GitHub Action, or Docker packaging — sub-project #6.

---

## 3. Architecture & data flow

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI  (Typer)   trustable init | validate | modules | version    │
└───────────────┬─────────────────────────────────────────────────┘
                │ reads
        ┌───────▼────────┐        ┌──────────────────────────────┐
        │  config/       │        │  plugins/                    │
        │  • schema      │        │  • capabilities (Protocols)  │
        │  • loader      │◄──────►│  • registry                  │
        │  • errors      │ 2-pass │  • discovery (entry-points)  │
        └───────┬────────┘ valid. │  • context (InteractionCtx)  │
                │                  └───────────────┬──────────────┘
                │ TrustableConfig                  │ ModuleSpecs
                └──────────────┬───────────────────┘
                       ┌───────▼─────────┐
                       │  runtime/       │  builds ordered pipeline
                       │  • runtime      │  from enabled modules
                       │  • pipeline     │  + their capabilities
                       └───────┬─────────┘
                               │ exposes engine API
        ┌──────────────────────▼───────────────────────────────┐
        │  Consumers:  SDK (sub-proj #2) wraps live LLM calls    │
        │              CLI module-commands (test/diff, later)    │
        └───────────────────────────────────────────────────────┘
```

**Runtime data flow** — one interaction passes through an ordered pipeline; a single
`InteractionContext` is threaded through every stage:

```
 request ─► [InputGuards]  ─► (blocked? → stop, return 400-style error)
              e.g. mask PII, scan injection   (may mutate ctx.prompt)
          ─► [Tracer.start]                    (audit: open span)
          ─► «host app's real LLM call happens here»   ◄── SDK owns this in #2
          ─► [Tracer.end]                      (audit: close span, tokens/latency)
          ─► [OutputGuards]                    (parse CoT, PII-leak check,
              (may mutate ctx.response,          RAG-context capture)
               append to ctx.records)
          ─► response + structured records
```

**Two invariants:**
- **Explicit ordering** — modules carry a `priority`; guards run deterministically.
- **Fail-open by default** — each module invocation is wrapped; a module that *throws* is logged
  and skipped so the host app's call still proceeds. The **only** intentional stop is a security
  guard setting `ctx.blocked` (a deliberate `400`, not a failure).

The Foundation delivers this engine fully working and proven with a reference module + tests. The
"wrap your `openai.chat(...)` call" ergonomics land in sub-project #2. Clean boundary:
**Foundation = the engine; SDK = the developer-facing wrapper that drives it.**

---

## 4. Config schema & two-pass validation

The core parser is deliberately **thin** — it does not hardcode each module's schema. Every module
owns its own config schema; the loader validates each module's block against the schema that module
registered.

**Core schema** (`config/schema.py`, Pydantic v2) — the envelope only:

```python
class PluginRef(BaseModel):
    ref: str          # "my_pkg.module:factory" import path OR an entry-point name

class RawModuleConfig(BaseModel):
    enabled: bool = False
    model_config = ConfigDict(extra="allow")   # module-specific keys pass through

class TrustableConfig(BaseModel):
    version: str = "1.0"
    project: str
    plugins: list[PluginRef] = []
    modules: dict[str, RawModuleConfig] = {}    # keyed by module name
```

**Two-pass validation** (`config/loader.py`):
1. **Pass 1 — envelope:** find `trustable.yaml` (walk up from cwd), parse YAML, validate against
   `TrustableConfig`. Catches malformed YAML, missing `project`, wrong types.
2. **Pass 2 — per module:** for each entry in `modules:`, look up its `ModuleSpec` in the registry
   and validate that module's raw block against `spec.config_model`.

Note the two related-but-distinct base classes:
- **`RawModuleConfig`** (Pass 1) is **lenient** — `extra="allow"` — so any module's keys survive
  the envelope parse untouched.
- **`ModuleConfig`** (Pass 2) is the **strict** base every module's own config extends:

```python
class ModuleConfig(BaseModel):
    enabled: bool = False
    model_config = ConfigDict(extra="forbid")   # unknown fields for THIS module → error
```

So Pass 2 catches both an **unknown module name** (no registered `ModuleSpec`) and an **unknown
field** within a known module (`extra="forbid"`).

The four PRD modules ship **registered with real config models + stub factories**, so
`trustable validate` gives genuine schema validation today:

```python
class SecurityConfig(ModuleConfig):        # ModuleConfig = enabled + module keys
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

This parses the exact PRD `trustable.yaml` unchanged. An unknown module key or bad value
(e.g. `log_level: "platinum"`) produces a precise error pointing at the offending field.

---

## 5. Plugin framework

**Capability protocols** (`plugins/capabilities.py`) — small, typed, `@runtime_checkable`. A module
implements only what it offers; the runtime introspects which protocols an instance satisfies and
slots it into the matching pipeline stages:

```python
@runtime_checkable
class InputGuard(Protocol):
    def check_input(self, ctx: InteractionContext) -> None: ...
    # may mutate ctx.prompt (masking) or set ctx.blocked (injection → stop)

@runtime_checkable
class OutputGuard(Protocol):
    def check_output(self, ctx: InteractionContext) -> None: ...
    # may mutate ctx.response or append to ctx.records

@runtime_checkable
class Tracer(Protocol):
    def start_trace(self, ctx: InteractionContext) -> None: ...
    def end_trace(self, ctx: InteractionContext) -> None: ...

@runtime_checkable
class CommandProvider(Protocol):
    def register_cli(self, app: "typer.Typer") -> None: ...   # adds subcommands
```

**Module descriptor** (`plugins/module.py`):

```python
@dataclass
class ModuleSpec:
    name: str                                   # "security", "audit", ...
    factory: Callable[[ModuleConfig], object]   # builds a configured instance
    config_model: type[ModuleConfig]            # this module's schema (Pass 2)
    priority: int = 100                          # lower = earlier in pipeline
```

**Registry** (`plugins/registry.py`) — in-memory `name → ModuleSpec` map; register/lookup/list,
with a clear error on duplicate names.

**Discovery** (`plugins/discovery.py`) — populates the registry from three sources, in order:
1. **Built-ins** — the four PRD module specs + the reference module, always registered.
2. **Entry-points** — anything advertising the `trustable.modules` group (third-party pip packages).
3. **Config `plugins:`** — explicit `ref` import paths from `trustable.yaml`, for local/in-repo
   custom modules not installed as packages.

A plugin that fails to import is **reported, not fatal** — `validate` and `modules list` surface it
as an error row; the rest keep working.

**InteractionContext** (`plugins/context.py`):

```python
@dataclass
class InteractionContext:
    prompt: Any
    response: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    records: list[dict] = field(default_factory=list)   # structured module output
    blocked: bool = False
    block_reason: str | None = None
```

**Runtime assembly** (`runtime/runtime.py` + `runtime/pipeline.py`):
- `TrustableRuntime.from_config(config)` resolves each **enabled** module via the registry, calls
  its `factory(validated_config)`, and sorts instances by `priority`.
- The `Pipeline` groups instances by capability and exposes `run_input_guards(ctx)`,
  `run_output_guards(ctx)`, and a `trace(ctx)` context manager. Each module call is wrapped for
  **fail-open** (log & skip on exception), except a guard setting `ctx.blocked`, which
  short-circuits input processing intentionally.

**Reference module** (`modules/noop/`) — a real registered module implementing all four
capabilities (harmless pass-throughs + one CLI subcommand). Proves the framework end-to-end and
serves as the copy-paste template for future modules.

---

## 6. CLI surface

| Command | Behavior |
|---|---|
| `trustable init [--force]` | Scaffold `trustable.yaml` (template matching the PRD) + starter dirs (`prompts/`, `tests/`). Refuses to overwrite unless `--force`. |
| `trustable validate [path]` | Run both validation passes; print friendly errors; exit non-zero on failure. CI-friendly gate. |
| `trustable modules list` | Table of discovered modules: name, enabled?, capabilities, source (built-in/entry-point/config), + import-error rows. |
| `trustable modules info <name>` | Show one module's config schema (fields, types, defaults) and capabilities. |
| `trustable version` / `--version` | Version + Python info. |

Module-provided subcommands (from `CommandProvider`) mount under the root app at startup, so later
`trustable test`, `trustable diff`, etc. attach without touching core CLI code.

---

## 7. Package layout

```
trustable/
├── pyproject.toml            # hatchling; declares `trustable.modules` entry-point group
├── src/trustable/
│   ├── __init__.py           # public API re-exports
│   ├── cli/                  # main, init, validate, modules
│   ├── config/               # schema, loader, errors
│   ├── plugins/              # capabilities, module, registry, discovery, context
│   ├── runtime/              # runtime, pipeline
│   ├── modules/noop/         # reference module
│   └── scaffold/             # templates for `init`
└── tests/                    # mirrors src/ layout
```

---

## 8. Error handling

- **Config-time → fail-loud.** Pydantic errors reshaped into readable messages (field path + what
  was expected), non-zero exit. This is where we are strict.
- **Runtime → fail-open.** Per-module try/except; a throwing module is logged and skipped so the
  host LLM call proceeds. Exception: an intentional `ctx.blocked` from a security guard.
- **Discovery → resilient.** A broken plugin becomes an error row, never a crash.

---

## 9. Testing strategy (pytest)

- **Config loader** — valid fixtures (incl. the exact PRD yaml) + invalid ones (bad `log_level`,
  missing `project`, unknown module key).
- **Registry/discovery** — built-in registration, a fake entry-point, a `plugins:` ref, and a
  deliberately-broken plugin surfacing as an error.
- **Pipeline** — ordering by priority, input/output mutation, `blocked` short-circuit, and
  **fail-open** (a throwing module doesn't break the pipeline).
- **CLI** — Typer's `CliRunner` over every command, asserting output + exit codes.
- **End-to-end** — the noop reference module driven through a full assembled pipeline with a fake
  `InteractionContext`.

---

## 10. Acceptance criteria

1. `pip install -e .` (or `uv` equivalent) exposes a working `trustable` CLI.
2. `trustable init` scaffolds a valid `trustable.yaml` + starter dirs; re-running without `--force`
   is refused.
3. `trustable validate` accepts the exact PRD `trustable.yaml` and rejects malformed configs with
   precise, friendly errors and a non-zero exit code.
4. `trustable modules list` shows the four built-in modules + the reference module, their enabled
   state, capabilities, and source; a broken plugin appears as an error row without crashing.
5. `trustable modules info security` prints the security module's config schema.
6. `TrustableRuntime.from_config(...)` assembles an ordered pipeline; input/output guards run in
   priority order; a `blocked` guard short-circuits; a throwing module is skipped (fail-open).
7. The noop reference module round-trips through the pipeline in an end-to-end test.
8. Full test suite passes; Ruff is clean.

---

## 11. Out of scope (future sub-projects)

SDK wrapper & auto-instrumentation (#2), real module behavior (#2–5), testing harness (#3),
security scanners (#4), prompts-as-code + GitHub Action (#5), Docker/CI + enterprise sinks (#6).
