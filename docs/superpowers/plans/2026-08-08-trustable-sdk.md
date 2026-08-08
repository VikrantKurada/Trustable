# Trustable SDK (Audit & Explainability) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the developer-facing SDK (`@trustable.trace` decorator + `trace()`/`atrace()` context-managers, sync & async) that drives the Foundation pipeline around a live model call, plus the real Audit (OpenTelemetry) and Explainability modules.

**Architecture:** A `trace` object usable three ways (bare decorator, parametrized decorator, context-manager) opens an `InteractionContext`, runs input guards, wraps the real call in the Foundation `Pipeline.trace(ctx)`, runs output guards, and returns. Audit is a `Tracer` that emits a real OTel span (lean `gen_ai.*` attributes) and writes local Bronze/Silver medallion JSONL directly from `ctx`. Explainability is an `OutputGuard` that normalizes RAG source-documents and extracts `<thinking>` reasoning into `ctx.records`.

**Tech Stack:** Python 3.11+, Typer/Pydantic v2/PyYAML (Foundation), OpenTelemetry (`opentelemetry-api` + `opentelemetry-sdk`, optional `[audit]` extra), pytest, Ruff, uv.

## Global Constraints

- Python **3.11+**. Run tooling via the existing uv venv: `uv run pytest`, `uv run ruff check`. Reinstall with `uv pip install -e ".[dev]"` after Task 1.
- Ruff lints against the repo's pinned config in `pyproject.toml` (`[tool.ruff.lint] select = ["E","F","I","UP","B","C4","SIM","BLE","RUF"]`). Broad `except Exception` in fail-open paths needs `# noqa: BLE001`. Keep imports isort-ordered (I001).
- **Fail-open at runtime** (the Foundation `Pipeline` already wraps each module call; modules must also not raise out of their own capability methods for foreseeable bad input — degrade and log). **Fail-loud at setup** (missing `[audit]` extra → clear error at runtime-build time).
- Module priorities are fixed by the Foundation: **explainability = 20, audit = 30**. Do not change them.
- Metadata key constants live in `src/trustable/keys.py` — import from there, never hard-code the strings.
- OpenTelemetry is imported **lazily inside `modules/audit/` only** — never at package import (`import trustable` and the CLI must work without the `[audit]` extra).
- No network in tests. Use OTel's `InMemorySpanExporter` and `tmp_path` JSONL files.
- ASCII only in user-facing strings (no em-dashes) — the repo targets Windows consoles.

---

## File Structure

```
src/trustable/
├── keys.py                     # NEW: shared metadata key constants
├── sdk/
│   ├── __init__.py             # NEW
│   ├── engine.py               # NEW: SdkRuntime (cached config→runtime)
│   ├── extract.py              # NEW: resolve_prompt / resolve_response
│   ├── current.py              # NEW: contextvar, use_current, get_current, record()
│   └── trace.py                # NEW: Blocked, _Trace, trace(), atrace()
├── modules/
│   ├── audit/
│   │   ├── __init__.py         # NEW
│   │   ├── otel.py             # NEW: require_otel, get_tracer, apply_gen_ai_attributes
│   │   ├── sinks.py            # NEW: build_bronze_record, build_silver_record, MedallionWriter
│   │   └── module.py           # NEW: AuditModule(Tracer) + audit_spec()
│   └── explainability/
│       ├── __init__.py         # NEW
│       ├── rag.py              # NEW: normalize_source_documents, extract_reasoning
│       └── module.py           # NEW: ExplainabilityModule(OutputGuard) + explainability_spec()
├── config/schema.py            # MODIFY: AuditConfig + ExplainabilityConfig fields
├── modules/builtins.py         # MODIFY: repoint audit/explainability to real specs
└── __init__.py                 # MODIFY: export trace, atrace, record, Blocked
pyproject.toml                  # MODIFY: [audit] extra + dev otel dep
```

---

## Task 1: Dependencies, shared keys & config-schema additions

**Files:**
- Modify: `pyproject.toml`
- Create: `src/trustable/keys.py`
- Modify: `src/trustable/config/schema.py`
- Test: `tests/config/test_schema.py` (append)

**Interfaces:**
- Consumes: existing `AuditConfig`, `ExplainabilityConfig`, `ModuleConfig`.
- Produces: `keys.{MODEL,RESPONSE_MODEL,INPUT_TOKENS,OUTPUT_TOKENS,SOURCE_DOCUMENTS,NAME,MANAGED,AUDIT_SPAN,AUDIT_START}` (all `str`); `AuditConfig.sink_path: str`, `AuditConfig.capture_payloads_as_events: bool`; `ExplainabilityConfig.extract_reasoning: bool`, `.reasoning_tag: str`, `.strip_reasoning: bool`.

- [ ] **Step 1: Add the optional extra and dev dep to `pyproject.toml`**

Replace the `[project.optional-dependencies]` block with:
```toml
[project.optional-dependencies]
audit = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]
dev = ["pytest>=8.0", "ruff>=0.5", "opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]
```

- [ ] **Step 2: Reinstall so OTel is available for the rest of the plan**

Run: `uv pip install -e ".[dev]"`
Expected: installs `opentelemetry-api` and `opentelemetry-sdk`.

- [ ] **Step 3: Create `src/trustable/keys.py`**

```python
"""Shared metadata keys used across the SDK and modules (avoids magic-string drift)."""

from __future__ import annotations

# Public keys a developer or an adapter may set on ctx.metadata.
MODEL = "model"
RESPONSE_MODEL = "response_model"
INPUT_TOKENS = "input_tokens"
OUTPUT_TOKENS = "output_tokens"
SOURCE_DOCUMENTS = "source_documents"
NAME = "name"

# Internal keys the SDK uses to thread state through one interaction.
MANAGED = "_trustable_managed"
AUDIT_SPAN = "_trustable_audit_span"
AUDIT_START = "_trustable_audit_start"
```

- [ ] **Step 4: Write the failing test** (append to `tests/config/test_schema.py`)

```python
def test_audit_config_new_fields_defaults():
    from trustable.config.schema import AuditConfig

    cfg = AuditConfig(enabled=True)
    assert cfg.sink_path == ".trustable/audit"
    assert cfg.capture_payloads_as_events is False


def test_explainability_config_new_fields_defaults():
    from trustable.config.schema import ExplainabilityConfig

    cfg = ExplainabilityConfig(enabled=True)
    assert cfg.extract_reasoning is True
    assert cfg.reasoning_tag == "thinking"
    assert cfg.strip_reasoning is True
```

- [ ] **Step 5: Run test to verify it fails**

Run: `uv run pytest tests/config/test_schema.py -k "new_fields" -v`
Expected: FAIL (unknown fields / attribute errors).

- [ ] **Step 6: Extend the config models** in `src/trustable/config/schema.py`

Replace the `AuditConfig` and `ExplainabilityConfig` classes with:
```python
class AuditConfig(ModuleConfig):
    sink: str = "local"
    log_level: Literal["bronze", "silver", "gold"] = "silver"
    sink_path: str = ".trustable/audit"
    capture_payloads_as_events: bool = False


class ExplainabilityConfig(ModuleConfig):
    capture_rag_context: bool = False
    extract_reasoning: bool = True
    reasoning_tag: str = "thinking"
    strip_reasoning: bool = True
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/config/test_schema.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml src/trustable/keys.py src/trustable/config/schema.py tests/config/test_schema.py
git commit -m "feat(sdk): add [audit] extra, shared keys, and audit/explainability config fields"
```

---

## Task 2: The active-interaction contextvar and `record()`

**Files:**
- Create: `src/trustable/sdk/__init__.py` (empty), `src/trustable/sdk/current.py`
- Test: `tests/sdk/test_current.py`

**Interfaces:**
- Consumes: `InteractionContext` (Foundation); `keys.SOURCE_DOCUMENTS`.
- Produces:
  - `get_current() -> InteractionContext | None`
  - `use_current(ctx: InteractionContext)` — a context manager that sets/resets the active ctx
  - `record(**fields: Any) -> None` — merges `fields` into the active ctx's `metadata`; no-op (debug log) if no active interaction.

- [ ] **Step 1: Write the failing test** (`tests/sdk/test_current.py`)

```python
from trustable.plugins.context import InteractionContext
from trustable.sdk.current import get_current, record, use_current


def test_no_active_interaction():
    assert get_current() is None
    record(source_documents=[{"id": "x"}])  # must not raise


def test_use_current_sets_and_resets():
    ctx = InteractionContext(prompt="hi")
    assert get_current() is None
    with use_current(ctx):
        assert get_current() is ctx
    assert get_current() is None


def test_record_merges_into_active_metadata():
    ctx = InteractionContext(prompt="hi")
    with use_current(ctx):
        record(source_documents=[{"id": "doc-1", "score": 0.9}], model="gpt-x")
    assert ctx.metadata["source_documents"] == [{"id": "doc-1", "score": 0.9}]
    assert ctx.metadata["model"] == "gpt-x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/sdk/test_current.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Create `src/trustable/sdk/__init__.py`** (empty) **and `src/trustable/sdk/current.py`**

```python
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from trustable.plugins.context import InteractionContext

logger = logging.getLogger("trustable.sdk")

_current: ContextVar[InteractionContext | None] = ContextVar("trustable_current", default=None)


def get_current() -> InteractionContext | None:
    return _current.get()


@contextmanager
def use_current(ctx: InteractionContext) -> Iterator[None]:
    token = _current.set(ctx)
    try:
        yield
    finally:
        _current.reset(token)


def record(**fields: Any) -> None:
    """Attach data to the active interaction's metadata (e.g. source_documents)."""
    ctx = get_current()
    if ctx is None:
        logger.debug("trustable.record() called outside a traced interaction; ignored")
        return
    ctx.metadata.update(fields)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/sdk/test_current.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/sdk/__init__.py src/trustable/sdk/current.py tests/sdk/test_current.py
git commit -m "feat(sdk): add active-interaction contextvar and record()"
```

---

## Task 3: Prompt/response extraction

**Files:**
- Create: `src/trustable/sdk/extract.py`
- Test: `tests/sdk/test_extract.py`

**Interfaces:**
- Consumes: nothing beyond stdlib `inspect`.
- Produces:
  - `resolve_prompt(fn: Callable, prompt: Callable | str | None, args: tuple, kwargs: dict) -> Any`
  - `resolve_response(response: Callable | None, result: Any) -> Any`
  - `CONVENTION_PROMPT_PARAMS = ("prompt", "messages")`

> Note: `response=` accepts a callable or `None` (convention = the return value). Unlike `prompt=`, a param-name string is **not** supported for `response` — a return value has no parameters.

- [ ] **Step 1: Write the failing test** (`tests/sdk/test_extract.py`)

```python
from trustable.sdk.extract import resolve_prompt, resolve_response


def fn_prompt(prompt): ...
def fn_messages(messages): ...
def fn_positional(x, y): ...
def fn_named(*, question): ...


def test_convention_prompt_kwarg():
    assert resolve_prompt(fn_prompt, None, (), {"prompt": "hi"}) == "hi"


def test_convention_messages_kwarg():
    assert resolve_prompt(fn_messages, None, (), {"messages": [1, 2]}) == [1, 2]


def test_convention_first_positional():
    assert resolve_prompt(fn_positional, None, ("p", "q"), {}) == "p"


def test_prompt_param_name_override():
    assert resolve_prompt(fn_named, "question", (), {"question": "why"}) == "why"


def test_prompt_callable_override():
    got = resolve_prompt(fn_named, lambda *a, **k: k["question"].upper(), (), {"question": "why"})
    assert got == "WHY"


def test_response_convention_is_return_value():
    assert resolve_response(None, {"answer": 1}) == {"answer": 1}


def test_response_callable_override():
    assert resolve_response(lambda r: r["answer"], {"answer": 42}) == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/sdk/test_extract.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/sdk/extract.py`**

```python
from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

CONVENTION_PROMPT_PARAMS = ("prompt", "messages")


def resolve_prompt(
    fn: Callable[..., Any], prompt: Callable[..., Any] | str | None, args: tuple, kwargs: dict
) -> Any:
    if callable(prompt):
        return prompt(*args, **kwargs)

    try:
        bound = inspect.signature(fn).bind_partial(*args, **kwargs)
    except TypeError:
        bound = None

    if isinstance(prompt, str):
        return bound.arguments.get(prompt) if bound is not None else None

    if bound is not None:
        for name in CONVENTION_PROMPT_PARAMS:
            if name in bound.arguments:
                return bound.arguments[name]
    return args[0] if args else None


def resolve_response(response: Callable[[Any], Any] | None, result: Any) -> Any:
    if callable(response):
        return response(result)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/sdk/test_extract.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/sdk/extract.py tests/sdk/test_extract.py
git commit -m "feat(sdk): add prompt/response extraction (convention + escape hatches)"
```

---

## Task 4: `SdkRuntime` (cached config → runtime)

**Files:**
- Create: `src/trustable/sdk/engine.py`
- Test: `tests/sdk/test_engine.py`

**Interfaces:**
- Consumes: `load_config`, `ModuleRegistry`, `TrustableRuntime` (Foundation).
- Produces: `SdkRuntime` with classmethods `get(config_path: str | None = None) -> TrustableRuntime`, `set(runtime: TrustableRuntime, config_path: str | None = None) -> None`, `reset() -> None`. Cache key is `str(config_path)` or `"<default>"`.

- [ ] **Step 1: Write the failing test** (`tests/sdk/test_engine.py`)

```python
from pathlib import Path

from trustable.runtime.runtime import TrustableRuntime
from trustable.sdk.engine import SdkRuntime

CONFIG = 'project: t\nmodules:\n  noop:\n    enabled: true\n'


def test_get_builds_and_caches(tmp_path: Path):
    SdkRuntime.reset()
    p = tmp_path / "trustable.yaml"
    p.write_text(CONFIG)
    rt1 = SdkRuntime.get(str(p))
    rt2 = SdkRuntime.get(str(p))
    assert isinstance(rt1, TrustableRuntime)
    assert rt1 is rt2  # cached
    assert any(m.__class__.__name__ == "NoopModule" for m in rt1.modules)


def test_set_and_reset():
    fake = TrustableRuntime.__new__(TrustableRuntime)
    SdkRuntime.set(fake)
    assert SdkRuntime.get() is fake
    SdkRuntime.reset()
    assert SdkRuntime._cache == {}  # reset cleared the cache
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/sdk/test_engine.py::test_get_builds_and_caches -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/sdk/engine.py`**

```python
from __future__ import annotations

from pathlib import Path

from trustable.config.loader import load_config
from trustable.plugins.registry import ModuleRegistry
from trustable.runtime.runtime import TrustableRuntime

_DEFAULT_KEY = "<default>"


class SdkRuntime:
    """Loads trustable.yaml once and caches the assembled runtime per config path."""

    _cache: dict[str, TrustableRuntime] = {}

    @classmethod
    def get(cls, config_path: str | None = None) -> TrustableRuntime:
        key = str(config_path) if config_path is not None else _DEFAULT_KEY
        runtime = cls._cache.get(key)
        if runtime is None:
            registry = ModuleRegistry()
            loaded = load_config(Path(config_path) if config_path is not None else None, registry)
            runtime = TrustableRuntime.from_config(
                loaded.config, loaded.module_configs, registry
            )
            cls._cache[key] = runtime
        return runtime

    @classmethod
    def set(cls, runtime: TrustableRuntime, config_path: str | None = None) -> None:
        cls._cache[str(config_path) if config_path is not None else _DEFAULT_KEY] = runtime

    @classmethod
    def reset(cls) -> None:
        cls._cache.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/sdk/test_engine.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/sdk/engine.py tests/sdk/test_engine.py
git commit -m "feat(sdk): add SdkRuntime with cached config-to-runtime"
```

---

## Task 5: `Blocked` + the sync `trace()` context-manager

**Files:**
- Create: `src/trustable/sdk/trace.py`
- Test: `tests/sdk/test_trace_cm.py`

**Interfaces:**
- Consumes: `SdkRuntime` (Task 4); `use_current` (Task 2); `InteractionContext`, `Pipeline` (Foundation); `keys.MANAGED`, `keys.NAME`.
- Produces:
  - `class Blocked(Exception)` with `.reason: str | None`
  - `_begin(prompt, name, managed, config_path) -> tuple[TrustableRuntime, InteractionContext]` (internal)
  - `_open_sync(prompt, name, managed, config_path)` — a `@contextmanager` yielding `ctx`
  - `class _Trace` supporting `__enter__`/`__exit__` (sync context-manager use)
  - `trace(fn=None, *, prompt=None, response=None, name=None, managed=False, config_path=None)` factory — returns a `_Trace`; if `fn` given (bare `@trace`) returns the decorated fn (decorator added in Task 6, so for now `_Trace.__call__` may be a stub raising `NotImplementedError`).

- [ ] **Step 1: Write the failing test** (`tests/sdk/test_trace_cm.py`)

```python
import pytest

from trustable.plugins.context import InteractionContext
from trustable.runtime.pipeline import Pipeline
from trustable.runtime.runtime import TrustableRuntime
from trustable.sdk.engine import SdkRuntime
from trustable.sdk import trace as trace_mod
from trustable.sdk.current import get_current


class RecordingTracer:
    def start_trace(self, ctx): ctx.records.append({"e": "start"})
    def end_trace(self, ctx): ctx.records.append({"e": "end"})


class RecordingOutput:
    def check_output(self, ctx): ctx.records.append({"e": "output", "resp": ctx.response})


class Blocker:
    def check_input(self, ctx):
        ctx.blocked = True
        ctx.block_reason = "nope"


def _runtime(modules):
    return TrustableRuntime(Pipeline(modules), modules)


@pytest.fixture(autouse=True)
def _reset():
    yield
    SdkRuntime.reset()


def test_cm_runs_start_output_end_in_order():
    SdkRuntime.set(_runtime([RecordingTracer(), RecordingOutput()]))
    with trace_mod.trace(prompt="hi", name="t") as ctx:
        assert get_current() is ctx
        ctx.response = "answer"
    assert [r["e"] for r in ctx.records] == ["start", "output", "end"]
    assert ctx.records[1]["resp"] == "answer"
    assert get_current() is None


def test_cm_blocked_raises():
    SdkRuntime.set(_runtime([Blocker()]))
    with pytest.raises(trace_mod.Blocked):
        with trace_mod.trace(prompt="hi"):
            pass


def test_cm_sets_managed_flag():
    from trustable import keys
    SdkRuntime.set(_runtime([]))
    with trace_mod.trace(prompt="hi", managed=True) as ctx:
        pass
    assert ctx.metadata[keys.MANAGED] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/sdk/test_trace_cm.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/sdk/trace.py`**

```python
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from trustable import keys
from trustable.plugins.context import InteractionContext
from trustable.runtime.runtime import TrustableRuntime
from trustable.sdk.current import use_current
from trustable.sdk.engine import SdkRuntime


class Blocked(Exception):
    """Raised when an input guard blocks an interaction (a deliberate stop)."""

    def __init__(self, reason: str | None = None) -> None:
        super().__init__(reason or "blocked")
        self.reason = reason


def _begin(
    prompt: Any, name: str | None, managed: bool, config_path: str | None
) -> tuple[TrustableRuntime, InteractionContext]:
    runtime = SdkRuntime.get(config_path)
    ctx = InteractionContext(prompt=prompt)
    ctx.metadata[keys.MANAGED] = managed
    if name:
        ctx.metadata[keys.NAME] = name
    runtime.pipeline.run_input_guards(ctx)
    if ctx.blocked:
        raise Blocked(ctx.block_reason)
    return runtime, ctx


@contextmanager
def _open_sync(
    prompt: Any, name: str | None, managed: bool, config_path: str | None
) -> Iterator[InteractionContext]:
    runtime, ctx = _begin(prompt, name, managed, config_path)
    with use_current(ctx), runtime.pipeline.trace(ctx):
        yield ctx
        runtime.pipeline.run_output_guards(ctx)


class _Trace:
    def __init__(
        self,
        *,
        prompt: Any = None,
        response: Callable[[Any], Any] | None = None,
        name: str | None = None,
        managed: bool = False,
        config_path: str | None = None,
    ) -> None:
        self.prompt = prompt
        self.response = response
        self.name = name
        self.managed = managed
        self.config_path = config_path
        self._cm: Any = None

    def __enter__(self) -> InteractionContext:
        self._cm = _open_sync(self.prompt, self.name, self.managed, self.config_path)
        return self._cm.__enter__()

    def __exit__(self, *exc: Any) -> bool | None:
        return self._cm.__exit__(*exc)

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        raise NotImplementedError("decorator use is added in Task 6")


def trace(
    fn: Callable[..., Any] | None = None,
    *,
    prompt: Any = None,
    response: Callable[[Any], Any] | None = None,
    name: str | None = None,
    managed: bool = False,
    config_path: str | None = None,
) -> Any:
    t = _Trace(
        prompt=prompt, response=response, name=name, managed=managed, config_path=config_path
    )
    return t(fn) if fn is not None else t
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/sdk/test_trace_cm.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/sdk/trace.py tests/sdk/test_trace_cm.py
git commit -m "feat(sdk): add Blocked and the sync trace() context-manager"
```

---

## Task 6: The sync `@trace` decorator

**Files:**
- Modify: `src/trustable/sdk/trace.py` (implement `_Trace.__call__` for sync fns)
- Test: `tests/sdk/test_trace_decorator.py`

**Interfaces:**
- Consumes: `resolve_prompt`, `resolve_response` (Task 3); `_open_sync` (Task 5).
- Produces: `_Trace.__call__(fn)` wrapping a sync `fn`; `@trace` (bare) and `@trace(...)` both work; returns `ctx.response` when `managed=True`, else the original result.

- [ ] **Step 1: Write the failing test** (`tests/sdk/test_trace_decorator.py`)

```python
import pytest

from trustable.runtime.pipeline import Pipeline
from trustable.runtime.runtime import TrustableRuntime
from trustable.sdk import trace as trace_mod
from trustable.sdk.engine import SdkRuntime


class StripGuard:
    """Output guard that rewrites ctx.response to prove managed mode returns it."""
    def check_output(self, ctx):
        if isinstance(ctx.response, str):
            ctx.response = ctx.response.replace("SECRET", "")


@pytest.fixture(autouse=True)
def _reset():
    SdkRuntime.set(TrustableRuntime(Pipeline([StripGuard()]), [StripGuard()]))
    yield
    SdkRuntime.reset()


def test_bare_decorator_observe_returns_original():
    @trace_mod.trace
    def answer(prompt):
        return prompt + " SECRET"

    assert answer("hi") == "hi SECRET"  # observe mode: original, untouched


def test_managed_returns_guard_modified():
    @trace_mod.trace(managed=True)
    def answer(prompt):
        return prompt + " SECRET"

    assert answer("hi") == "hi "  # managed mode: guard-stripped ctx.response


def test_response_extractor():
    @trace_mod.trace(response=lambda r: r["text"])
    def answer(prompt):
        return {"text": "ok"}

    assert answer("hi") == {"text": "ok"}  # observe returns original object
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/sdk/test_trace_decorator.py -v`
Expected: FAIL (`NotImplementedError`).

- [ ] **Step 3: Implement `_Trace.__call__` and a sync wrapper** in `src/trustable/sdk/trace.py`

Add these imports to the top of `trace.py` (merge with existing):
```python
from functools import wraps

from trustable.sdk.extract import resolve_prompt, resolve_response
```
Replace `_Trace.__call__` with:
```python
    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        return self._wrap_sync(fn)

    def _wrap_sync(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def inner(*args: Any, **kwargs: Any) -> Any:
            prompt = resolve_prompt(fn, self.prompt, args, kwargs)
            with _open_sync(prompt, self.name or fn.__name__, self.managed, self.config_path) as ctx:
                result = fn(*args, **kwargs)
                ctx.response = resolve_response(self.response, result)
            return ctx.response if self.managed else result

        return inner
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/sdk/test_trace_decorator.py tests/sdk/test_trace_cm.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/sdk/trace.py tests/sdk/test_trace_decorator.py
git commit -m "feat(sdk): add the sync @trace decorator with observe/managed return"
```

---

## Task 7: Async support (`atrace` + async decorator)

**Files:**
- Modify: `src/trustable/sdk/trace.py` (async CM helpers, `_Trace.__aenter__/__aexit__`, async wrapper, `atrace`)
- Test: `tests/sdk/test_trace_async.py`

**Interfaces:**
- Consumes: everything from Tasks 5-6.
- Produces: `_open_async(...)` (`@asynccontextmanager`); `_Trace.__aenter__ -> InteractionContext`, `_Trace.__aexit__`; async branch in `_Trace.__call__` via `inspect.iscoroutinefunction`; `atrace(fn=None, *, ...)` factory (same options as `trace`).

- [ ] **Step 1: Write the failing test** (`tests/sdk/test_trace_async.py`)

```python
import asyncio

import pytest

from trustable.runtime.pipeline import Pipeline
from trustable.runtime.runtime import TrustableRuntime
from trustable.sdk import trace as trace_mod
from trustable.sdk.engine import SdkRuntime


class RecordingTracer:
    def start_trace(self, ctx): ctx.records.append("start")
    def end_trace(self, ctx): ctx.records.append("end")


@pytest.fixture(autouse=True)
def _reset():
    SdkRuntime.set(TrustableRuntime(Pipeline([RecordingTracer()]), [RecordingTracer()]))
    yield
    SdkRuntime.reset()


def test_async_decorator():
    @trace_mod.trace
    async def answer(prompt):
        return prompt + "!"

    assert asyncio.run(answer("hi")) == "hi!"


def test_async_context_manager():
    async def run():
        async with trace_mod.atrace(prompt="hi", name="a") as ctx:
            ctx.response = "done"
        return ctx.records

    assert asyncio.run(run()) == ["start", "end"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/sdk/test_trace_async.py -v`
Expected: FAIL (`AttributeError: atrace` / coroutine not awaited).

- [ ] **Step 3: Add async support** to `src/trustable/sdk/trace.py`

Add to the imports at the top (merge):
```python
import inspect
from collections.abc import Awaitable
from contextlib import asynccontextmanager
```
Add after `_open_sync`:
```python
@asynccontextmanager
async def _open_async(
    prompt: Any, name: str | None, managed: bool, config_path: str | None
) -> Any:
    runtime, ctx = _begin(prompt, name, managed, config_path)
    with use_current(ctx), runtime.pipeline.trace(ctx):
        yield ctx
        runtime.pipeline.run_output_guards(ctx)
```
Add these methods to `_Trace` (alongside `__enter__`/`__exit__`):
```python
    async def __aenter__(self) -> InteractionContext:
        self._acm = _open_async(self.prompt, self.name, self.managed, self.config_path)
        return await self._acm.__aenter__()

    async def __aexit__(self, *exc: Any) -> bool | None:
        return await self._acm.__aexit__(*exc)
```
Update `_Trace.__call__` to branch on coroutine functions:
```python
    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(fn):
            return self._wrap_async(fn)
        return self._wrap_sync(fn)

    def _wrap_async(self, fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(fn)
        async def inner(*args: Any, **kwargs: Any) -> Any:
            prompt = resolve_prompt(fn, self.prompt, args, kwargs)
            async with _open_async(
                prompt, self.name or fn.__name__, self.managed, self.config_path
            ) as ctx:
                result = await fn(*args, **kwargs)
                ctx.response = resolve_response(self.response, result)
            return ctx.response if self.managed else result

        return inner
```
Add `atrace` next to `trace` (identical factory — `_Trace` already supports the async protocol; a distinct name reads clearly for `async with`):
```python
def atrace(
    fn: Callable[..., Any] | None = None,
    *,
    prompt: Any = None,
    response: Callable[[Any], Any] | None = None,
    name: str | None = None,
    managed: bool = False,
    config_path: str | None = None,
) -> Any:
    t = _Trace(
        prompt=prompt, response=response, name=name, managed=managed, config_path=config_path
    )
    return t(fn) if fn is not None else t
```
Also add `self._acm: Any = None` in `_Trace.__init__` next to `self._cm`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/sdk/ -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/sdk/trace.py tests/sdk/test_trace_async.py
git commit -m "feat(sdk): add async atrace() and async @trace decorator"
```

---

## Task 8: Audit — OTel helpers (`otel.py`)

**Files:**
- Create: `src/trustable/modules/audit/__init__.py` (empty), `src/trustable/modules/audit/otel.py`
- Test: `tests/modules/audit/test_otel.py`

**Interfaces:**
- Consumes: `InteractionContext`; `keys.{MODEL,RESPONSE_MODEL,INPUT_TOKENS,OUTPUT_TOKENS}`; `opentelemetry` (lazy).
- Produces:
  - `class AuditDependencyError(RuntimeError)`
  - `require_otel() -> None` (raises `AuditDependencyError` if OTel not importable)
  - `get_tracer() -> Any` (ensures a global `TracerProvider`, returns a tracer named `"trustable"`)
  - `apply_gen_ai_attributes(span: Any, ctx: InteractionContext) -> None`
  - `_HAS_OTEL: bool`

- [ ] **Step 1: Write the failing test** (`tests/modules/audit/test_otel.py`)

```python
import pytest

from trustable import keys
from trustable.plugins.context import InteractionContext


def test_require_otel_raises_when_missing(monkeypatch):
    from trustable.modules.audit import otel

    monkeypatch.setattr(otel, "_HAS_OTEL", False)
    with pytest.raises(otel.AuditDependencyError) as exc:
        otel.require_otel()
    assert "trustable[audit]" in str(exc.value)


def test_apply_gen_ai_attributes():
    from opentelemetry.sdk.trace import TracerProvider

    from trustable.modules.audit import otel

    provider = TracerProvider()
    tracer = provider.get_tracer("test")
    ctx = InteractionContext(prompt="hi")
    ctx.metadata[keys.MODEL] = "gpt-x"
    ctx.metadata[keys.INPUT_TOKENS] = 12
    ctx.metadata[keys.OUTPUT_TOKENS] = 34

    span = tracer.start_span("chat")
    otel.apply_gen_ai_attributes(span, ctx)
    span.end()

    attrs = span.attributes
    assert attrs["gen_ai.request.model"] == "gpt-x"
    assert attrs["gen_ai.usage.input_tokens"] == 12
    assert attrs["gen_ai.usage.output_tokens"] == 34
    assert attrs["trustable.records"] == 0
    assert attrs["trustable.blocked"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/modules/audit/test_otel.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Create `src/trustable/modules/audit/__init__.py`** (empty) **and `src/trustable/modules/audit/otel.py`**

```python
from __future__ import annotations

from typing import Any

from trustable import keys
from trustable.plugins.context import InteractionContext

try:
    from opentelemetry import trace as _ot_trace
    from opentelemetry.sdk.trace import TracerProvider

    _HAS_OTEL = True
except ImportError:  # pragma: no cover - exercised via monkeypatch
    _HAS_OTEL = False


class AuditDependencyError(RuntimeError):
    """Raised when the audit module is enabled without the OpenTelemetry extra."""


def require_otel() -> None:
    if not _HAS_OTEL:
        raise AuditDependencyError(
            "The 'audit' module requires OpenTelemetry. Install it with: pip install trustable[audit]"
        )


def get_tracer() -> Any:
    require_otel()
    provider = _ot_trace.get_tracer_provider()
    # get_tracer_provider() returns a no-op proxy until one is set; install a real one once.
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        _ot_trace.set_tracer_provider(provider)
    return _ot_trace.get_tracer("trustable")


def apply_gen_ai_attributes(span: Any, ctx: InteractionContext) -> None:
    md = ctx.metadata
    if keys.MODEL in md:
        span.set_attribute("gen_ai.request.model", md[keys.MODEL])
    if keys.RESPONSE_MODEL in md:
        span.set_attribute("gen_ai.response.model", md[keys.RESPONSE_MODEL])
    if keys.INPUT_TOKENS in md:
        span.set_attribute("gen_ai.usage.input_tokens", md[keys.INPUT_TOKENS])
    if keys.OUTPUT_TOKENS in md:
        span.set_attribute("gen_ai.usage.output_tokens", md[keys.OUTPUT_TOKENS])
    span.set_attribute("trustable.records", len(ctx.records))
    span.set_attribute("trustable.blocked", ctx.blocked)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/modules/audit/test_otel.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/modules/audit/__init__.py src/trustable/modules/audit/otel.py tests/modules/audit/test_otel.py
git commit -m "feat(audit): add OTel helpers (require_otel, tracer, gen_ai attributes)"
```

---

## Task 9: Audit — medallion sinks (`sinks.py`)

**Files:**
- Create: `src/trustable/modules/audit/sinks.py`
- Test: `tests/modules/audit/test_sinks.py`

**Interfaces:**
- Consumes: `InteractionContext`; `keys.*`.
- Produces:
  - `build_bronze_record(ctx: InteractionContext, latency_ms: float) -> dict`
  - `build_silver_record(ctx: InteractionContext, latency_ms: float) -> dict`
  - `class MedallionWriter` — `__init__(self, sink_path: str, log_level: str)`, `write(self, ctx: InteractionContext, latency_ms: float) -> None`. Writes `bronze.jsonl` always; `silver.jsonl` when `log_level` in `{"silver","gold"}`; Gold is a logged no-op.

- [ ] **Step 1: Write the failing test** (`tests/modules/audit/test_sinks.py`)

```python
import json
from pathlib import Path

from trustable import keys
from trustable.plugins.context import InteractionContext
from trustable.modules.audit.sinks import (
    MedallionWriter,
    build_bronze_record,
    build_silver_record,
)


def _ctx():
    ctx = InteractionContext(prompt="hi")
    ctx.response = "there"
    ctx.metadata[keys.NAME] = "chat"
    ctx.metadata[keys.MODEL] = "gpt-x"
    ctx.metadata[keys.INPUT_TOKENS] = 3
    ctx.records.append({"type": "reasoning", "content": "because"})
    return ctx


def test_silver_record_is_flattened():
    rec = build_silver_record(_ctx(), 12.5)
    assert rec["prompt"] == "hi"
    assert rec["response"] == "there"
    assert rec["name"] == "chat"
    assert rec["model"] == "gpt-x"
    assert rec["latency_ms"] == 12.5
    assert rec["reasoning"] == "because"


def test_bronze_has_full_records():
    rec = build_bronze_record(_ctx(), 12.5)
    assert rec["records"] == [{"type": "reasoning", "content": "because"}]
    assert rec["metadata"]["model"] == "gpt-x"


def test_writer_bronze_only(tmp_path: Path):
    MedallionWriter(str(tmp_path), "bronze").write(_ctx(), 1.0)
    assert (tmp_path / "bronze.jsonl").exists()
    assert not (tmp_path / "silver.jsonl").exists()


def test_writer_silver_writes_both(tmp_path: Path):
    w = MedallionWriter(str(tmp_path), "silver")
    w.write(_ctx(), 1.0)
    w.write(_ctx(), 2.0)
    silver_lines = (tmp_path / "silver.jsonl").read_text().strip().splitlines()
    assert len(silver_lines) == 2
    assert json.loads(silver_lines[0])["response"] == "there"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/modules/audit/test_sinks.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/modules/audit/sinks.py`**

```python
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from trustable import keys
from trustable.plugins.context import InteractionContext

logger = logging.getLogger("trustable.audit")

_INTERNAL_KEYS = {keys.MANAGED, keys.AUDIT_SPAN, keys.AUDIT_START}


def _public_metadata(ctx: InteractionContext) -> dict[str, Any]:
    return {k: v for k, v in ctx.metadata.items() if k not in _INTERNAL_KEYS}


def _first_reasoning(ctx: InteractionContext) -> str | None:
    for rec in ctx.records:
        if rec.get("type") == "reasoning":
            return rec.get("content")
    return None


def build_bronze_record(ctx: InteractionContext, latency_ms: float) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "name": ctx.metadata.get(keys.NAME),
        "prompt": ctx.prompt,
        "response": ctx.response,
        "blocked": ctx.blocked,
        "latency_ms": latency_ms,
        "metadata": _public_metadata(ctx),
        "records": list(ctx.records),
    }


def build_silver_record(ctx: InteractionContext, latency_ms: float) -> dict[str, Any]:
    md = ctx.metadata
    return {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "name": md.get(keys.NAME),
        "model": md.get(keys.MODEL),
        "prompt": ctx.prompt,
        "response": ctx.response,
        "input_tokens": md.get(keys.INPUT_TOKENS),
        "output_tokens": md.get(keys.OUTPUT_TOKENS),
        "latency_ms": latency_ms,
        "source_documents": md.get(keys.SOURCE_DOCUMENTS),
        "reasoning": _first_reasoning(ctx),
    }


class MedallionWriter:
    """Writes local medallion-tiered audit JSONL directly from the InteractionContext."""

    def __init__(self, sink_path: str, log_level: str) -> None:
        self._dir = Path(sink_path)
        self._level = log_level

    def _append(self, filename: str, record: dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with (self._dir / filename).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")

    def write(self, ctx: InteractionContext, latency_ms: float) -> None:
        self._append("bronze.jsonl", build_bronze_record(ctx, latency_ms))
        if self._level in ("silver", "gold"):
            self._append("silver.jsonl", build_silver_record(ctx, latency_ms))
        if self._level == "gold":
            logger.debug("gold-tier aggregation is not implemented yet; skipping")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/modules/audit/test_sinks.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/modules/audit/sinks.py tests/modules/audit/test_sinks.py
git commit -m "feat(audit): add medallion sink record shaping and JSONL writer"
```

---

## Task 10: Audit — the module (`module.py`) + `audit_spec()`

**Files:**
- Create: `src/trustable/modules/audit/module.py`
- Test: `tests/modules/audit/test_module.py`

**Interfaces:**
- Consumes: `otel.{require_otel,get_tracer,apply_gen_ai_attributes}` (Task 8); `MedallionWriter` (Task 9); `AuditConfig`; `ModuleSpec`; `keys.{AUDIT_SPAN,AUDIT_START,NAME}`.
- Produces:
  - `class AuditModule` — `__init__(self, config: AuditConfig)` (calls `require_otel()`); `start_trace(ctx)`; `end_trace(ctx)` (implements the `Tracer` protocol).
  - `audit_spec() -> ModuleSpec` (name `"audit"`, factory `lambda c: AuditModule(c)`, config_model `AuditConfig`, priority `30`).

- [ ] **Step 1: Write the failing test** (`tests/modules/audit/test_module.py`)

```python
from pathlib import Path

from trustable import keys
from trustable.config.schema import AuditConfig
from trustable.plugins.capabilities import Tracer
from trustable.plugins.context import InteractionContext
from trustable.modules.audit.module import AuditModule, audit_spec


def test_audit_spec_metadata():
    spec = audit_spec()
    assert spec.name == "audit"
    assert spec.priority == 30
    assert spec.config_model is AuditConfig


def test_audit_module_is_a_tracer_and_writes_silver(tmp_path: Path):
    cfg = AuditConfig(enabled=True, log_level="silver", sink_path=str(tmp_path))
    mod = AuditModule(cfg)
    assert isinstance(mod, Tracer)

    ctx = InteractionContext(prompt="hi")
    ctx.metadata[keys.MODEL] = "gpt-x"
    mod.start_trace(ctx)
    ctx.response = "there"
    mod.end_trace(ctx)

    silver = (tmp_path / "silver.jsonl").read_text().strip()
    assert '"response": "there"' in silver
    assert (tmp_path / "bronze.jsonl").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/modules/audit/test_module.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/modules/audit/module.py`**

```python
from __future__ import annotations

import logging
import time

from trustable import keys
from trustable.config.schema import AuditConfig
from trustable.modules.audit.otel import (
    apply_gen_ai_attributes,
    get_tracer,
    require_otel,
)
from trustable.modules.audit.sinks import MedallionWriter
from trustable.plugins.context import InteractionContext
from trustable.plugins.module import ModuleSpec

logger = logging.getLogger("trustable.audit")


class AuditModule:
    """Tracer: one OTel span per interaction + local medallion sinks written from ctx."""

    def __init__(self, config: AuditConfig) -> None:
        require_otel()  # fail loud at build time if the [audit] extra is missing
        self.config = config
        self._tracer = get_tracer()
        self._writer = MedallionWriter(config.sink_path, config.log_level)

    def start_trace(self, ctx: InteractionContext) -> None:
        name = ctx.metadata.get(keys.NAME) or "trustable.interaction"
        ctx.metadata[keys.AUDIT_SPAN] = self._tracer.start_span(name)
        ctx.metadata[keys.AUDIT_START] = time.perf_counter()

    def end_trace(self, ctx: InteractionContext) -> None:
        span = ctx.metadata.pop(keys.AUDIT_SPAN, None)
        start = ctx.metadata.pop(keys.AUDIT_START, None)
        latency_ms = (time.perf_counter() - start) * 1000.0 if start is not None else 0.0
        if span is not None:
            apply_gen_ai_attributes(span, ctx)
            span.set_attribute("trustable.latency_ms", latency_ms)
            if self.config.capture_payloads_as_events:
                span.add_event("trustable.payload", {"prompt": str(ctx.prompt), "response": str(ctx.response)})
            span.end()
        self._writer.write(ctx, latency_ms)


def audit_spec() -> ModuleSpec:
    return ModuleSpec(
        name="audit", factory=lambda c: AuditModule(c), config_model=AuditConfig, priority=30
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/modules/audit/ -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/modules/audit/module.py tests/modules/audit/test_module.py
git commit -m "feat(audit): add AuditModule (OTel span + medallion sinks) and audit_spec"
```

---

## Task 11: Explainability — RAG normalizer & CoT extraction (`rag.py`)

**Files:**
- Create: `src/trustable/modules/explainability/__init__.py` (empty), `src/trustable/modules/explainability/rag.py`
- Test: `tests/modules/explainability/test_rag.py`

**Interfaces:**
- Consumes: nothing beyond stdlib `re`.
- Produces:
  - `normalize_source_documents(docs: Any) -> list[dict]` — accepts a list of dicts, `(text, score)` tuples, or objects with `.page_content`/`.metadata` (LangChain `Document`); degrades gracefully, never raises.
  - `extract_reasoning(text: str, tag: str) -> tuple[str | None, str]` — returns `(reasoning_or_None, stripped_text)`.

- [ ] **Step 1: Write the failing test** (`tests/modules/explainability/test_rag.py`)

```python
from trustable.modules.explainability.rag import (
    extract_reasoning,
    normalize_source_documents,
)


class FakeDoc:
    def __init__(self, content, meta):
        self.page_content = content
        self.metadata = meta


def test_normalize_dicts():
    out = normalize_source_documents([{"id": "d1", "score": 0.8, "content": "abc"}])
    assert out == [{"id": "d1", "score": 0.8, "content": "abc", "metadata": {}}]


def test_normalize_tuples():
    out = normalize_source_documents([("some text", 0.5)])
    assert out[0]["content"] == "some text"
    assert out[0]["score"] == 0.5


def test_normalize_langchain_like():
    out = normalize_source_documents([FakeDoc("body", {"source": "f.pdf"})])
    assert out[0]["content"] == "body"
    assert out[0]["metadata"] == {"source": "f.pdf"}


def test_normalize_degrades_on_junk():
    out = normalize_source_documents([42, None])
    assert len(out) == 2
    assert all("content" in d for d in out)


def test_extract_reasoning_found():
    reasoning, stripped = extract_reasoning("<thinking>step 1</thinking>Answer.", "thinking")
    assert reasoning == "step 1"
    assert stripped == "Answer."


def test_extract_reasoning_absent():
    reasoning, stripped = extract_reasoning("Just an answer.", "thinking")
    assert reasoning is None
    assert stripped == "Just an answer."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/modules/explainability/test_rag.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/modules/explainability/__init__.py`** (empty) **and `src/trustable/modules/explainability/rag.py`**

```python
from __future__ import annotations

import re
from typing import Any


def _normalize_one(doc: Any) -> dict[str, Any]:
    if isinstance(doc, dict):
        return {
            "id": doc.get("id"),
            "score": doc.get("score"),
            "content": doc.get("content") or doc.get("page_content") or doc.get("text"),
            "metadata": doc.get("metadata", {}),
        }
    if isinstance(doc, tuple) and len(doc) == 2:
        text, score = doc
        return {"id": None, "score": score, "content": text, "metadata": {}}
    page_content = getattr(doc, "page_content", None)
    if page_content is not None:
        return {
            "id": getattr(doc, "id", None),
            "score": getattr(doc, "score", None),
            "content": page_content,
            "metadata": getattr(doc, "metadata", {}) or {},
        }
    return {"id": None, "score": None, "content": str(doc), "metadata": {}}


def normalize_source_documents(docs: Any) -> list[dict[str, Any]]:
    if not isinstance(docs, (list, tuple)):
        docs = [docs]
    return [_normalize_one(d) for d in docs]


def extract_reasoning(text: str, tag: str) -> tuple[str | None, str]:
    pattern = re.compile(rf"<{re.escape(tag)}>(.*?)</{re.escape(tag)}>", re.DOTALL)
    match = pattern.search(text)
    if match is None:
        return None, text
    reasoning = match.group(1).strip()
    stripped = pattern.sub("", text, count=1).strip()
    return reasoning, stripped
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/modules/explainability/test_rag.py -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/modules/explainability/__init__.py src/trustable/modules/explainability/rag.py tests/modules/explainability/test_rag.py
git commit -m "feat(explainability): add RAG source-doc normalizer and CoT extraction"
```

---

## Task 12: Explainability — the module (`module.py`) + `explainability_spec()`

**Files:**
- Create: `src/trustable/modules/explainability/module.py`
- Test: `tests/modules/explainability/test_module.py`

**Interfaces:**
- Consumes: `normalize_source_documents`, `extract_reasoning` (Task 11); `ExplainabilityConfig`; `ModuleSpec`; `keys.{SOURCE_DOCUMENTS,MANAGED}`.
- Produces:
  - `class ExplainabilityModule` — `__init__(self, config: ExplainabilityConfig)`; `check_output(ctx)` (implements `OutputGuard`).
  - `explainability_spec() -> ModuleSpec` (name `"explainability"`, priority `20`, config_model `ExplainabilityConfig`).

Behavior of `check_output(ctx)`:
- If `capture_rag_context` and `ctx.metadata` has `source_documents`: append `{"type": "rag_context", "source_documents": normalize_source_documents(...)}` to `ctx.records`.
- If `extract_reasoning` and `ctx.response` is a `str`: `reasoning, stripped = extract_reasoning(ctx.response, reasoning_tag)`; if reasoning is not None, append `{"type": "reasoning", "content": reasoning}`; then if `strip_reasoning` **and** `ctx.metadata.get(keys.MANAGED)` is true, set `ctx.response = stripped`.

- [ ] **Step 1: Write the failing test** (`tests/modules/explainability/test_module.py`)

```python
from trustable import keys
from trustable.config.schema import ExplainabilityConfig
from trustable.plugins.capabilities import OutputGuard
from trustable.plugins.context import InteractionContext
from trustable.modules.explainability.module import (
    ExplainabilityModule,
    explainability_spec,
)


def test_spec_metadata():
    spec = explainability_spec()
    assert spec.name == "explainability"
    assert spec.priority == 20


def test_captures_rag_context():
    mod = ExplainabilityModule(ExplainabilityConfig(enabled=True, capture_rag_context=True))
    ctx = InteractionContext(prompt="q")
    ctx.metadata[keys.SOURCE_DOCUMENTS] = [{"id": "d1", "score": 0.9, "content": "c"}]
    assert isinstance(mod, OutputGuard)
    mod.check_output(ctx)
    rag = [r for r in ctx.records if r["type"] == "rag_context"]
    assert rag and rag[0]["source_documents"][0]["id"] == "d1"


def test_managed_strips_reasoning():
    mod = ExplainabilityModule(ExplainabilityConfig(enabled=True))
    ctx = InteractionContext(prompt="q")
    ctx.metadata[keys.MANAGED] = True
    ctx.response = "<thinking>because</thinking>Final."
    mod.check_output(ctx)
    assert ctx.response == "Final."
    assert any(r["type"] == "reasoning" and r["content"] == "because" for r in ctx.records)


def test_observe_records_but_keeps_response():
    mod = ExplainabilityModule(ExplainabilityConfig(enabled=True))
    ctx = InteractionContext(prompt="q")
    ctx.metadata[keys.MANAGED] = False
    ctx.response = "<thinking>because</thinking>Final."
    mod.check_output(ctx)
    assert ctx.response == "<thinking>because</thinking>Final."  # unchanged
    assert any(r["type"] == "reasoning" for r in ctx.records)  # still recorded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/modules/explainability/test_module.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write `src/trustable/modules/explainability/module.py`**

```python
from __future__ import annotations

from trustable import keys
from trustable.config.schema import ExplainabilityConfig
from trustable.modules.explainability.rag import (
    extract_reasoning,
    normalize_source_documents,
)
from trustable.plugins.context import InteractionContext
from trustable.plugins.module import ModuleSpec


class ExplainabilityModule:
    """OutputGuard: capture RAG lineage and extract chain-of-thought into ctx.records."""

    def __init__(self, config: ExplainabilityConfig) -> None:
        self.config = config

    def check_output(self, ctx: InteractionContext) -> None:
        if self.config.capture_rag_context and keys.SOURCE_DOCUMENTS in ctx.metadata:
            ctx.records.append(
                {
                    "type": "rag_context",
                    "source_documents": normalize_source_documents(
                        ctx.metadata[keys.SOURCE_DOCUMENTS]
                    ),
                }
            )

        if self.config.extract_reasoning and isinstance(ctx.response, str):
            reasoning, stripped = extract_reasoning(ctx.response, self.config.reasoning_tag)
            if reasoning is not None:
                ctx.records.append({"type": "reasoning", "content": reasoning})
                if self.config.strip_reasoning and ctx.metadata.get(keys.MANAGED):
                    ctx.response = stripped


def explainability_spec() -> ModuleSpec:
    return ModuleSpec(
        name="explainability",
        factory=lambda c: ExplainabilityModule(c),
        config_model=ExplainabilityConfig,
        priority=20,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/modules/explainability/ -v && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/trustable/modules/explainability/module.py tests/modules/explainability/test_module.py
git commit -m "feat(explainability): add ExplainabilityModule (RAG + CoT) and spec"
```

---

## Task 13: Wire it up — repoint built-ins & export the public API

**Files:**
- Modify: `src/trustable/modules/builtins.py`
- Modify: `src/trustable/__init__.py`
- Test: `tests/modules/test_builtins.py` (append), `tests/sdk/test_public_api.py`

**Interfaces:**
- Consumes: `audit_spec` (Task 10), `explainability_spec` (Task 12); `trace`, `atrace`, `Blocked` (Task 7), `record` (Task 2).
- Produces: `trustable.trace`, `trustable.atrace`, `trustable.record`, `trustable.Blocked` importable from the package root; `register_builtins` registers the real audit/explainability specs.

- [ ] **Step 1: Write the failing tests**

Append to `tests/modules/test_builtins.py`:
```python
def test_audit_and_explainability_are_real_specs():
    from trustable.config.schema import AuditConfig, ExplainabilityConfig
    from trustable.plugins.capabilities import OutputGuard, Tracer
    from trustable.plugins.registry import ModuleRegistry

    reg = ModuleRegistry()
    register_builtins(reg)

    audit = reg.get("audit")
    assert audit.priority == 30 and audit.config_model is AuditConfig
    expl = reg.get("explainability")
    assert expl.priority == 20 and expl.config_model is ExplainabilityConfig

    # explainability builds without OTel and is an OutputGuard
    inst = expl.factory(ExplainabilityConfig(enabled=True))
    assert isinstance(inst, OutputGuard)
    # audit builds (OTel present in dev) and is a Tracer
    assert isinstance(audit.factory(AuditConfig(enabled=True, sink_path=".trustable/audit")), Tracer)
```

Create `tests/sdk/test_public_api.py`:
```python
import trustable


def test_public_api_exports():
    assert callable(trustable.trace)
    assert callable(trustable.atrace)
    assert callable(trustable.record)
    assert issubclass(trustable.Blocked, Exception)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/sdk/test_public_api.py tests/modules/test_builtins.py -v`
Expected: FAIL (attribute/spec errors).

- [ ] **Step 3: Repoint `register_builtins`** in `src/trustable/modules/builtins.py`

Replace the top-of-file import block (this **drops** the now-unused `AuditConfig`/`ExplainabilityConfig` and **adds** the two real specs, isort-ordered):
```python
from trustable.config.schema import ModuleConfig, SecurityConfig, TestConfig
from trustable.modules.audit.module import audit_spec
from trustable.modules.explainability.module import explainability_spec
from trustable.modules.noop import noop_spec
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import ModuleRegistry
```
Then replace the two `_stub_spec` registrations for explainability and audit inside `register_builtins`:
```python
def register_builtins(registry: ModuleRegistry) -> None:
    registry.register(_stub_spec("security", SecurityConfig, 10))
    registry.register(explainability_spec())
    registry.register(audit_spec())
    registry.register(noop_spec())
    registry.register(_stub_spec("test", TestConfig, 100))
```
(`ModuleConfig` stays — `_StubModule`/`_stub_spec` still use it for security and test.)

- [ ] **Step 4: Export the SDK API** in `src/trustable/__init__.py`

Add imports (merge, isort order):
```python
from trustable.sdk.current import record
from trustable.sdk.trace import Blocked, atrace, trace
```
Add `"Blocked"`, `"atrace"`, `"record"`, `"trace"` to `__all__` (keep it sorted).

- [ ] **Step 5: Run the full suite to verify nothing regressed**

Run: `uv run pytest -q && uv run ruff check src tests`
Expected: PASS, ruff clean. (Note: importing `trustable` now imports the SDK, which imports the audit module lazily — confirm `import trustable` still works with OTel installed; the lazy guard means it also works without.)

- [ ] **Step 6: Commit**

```bash
git add src/trustable/modules/builtins.py src/trustable/__init__.py tests/modules/test_builtins.py tests/sdk/test_public_api.py
git commit -m "feat(sdk): repoint audit/explainability built-ins and export trace/atrace/record/Blocked"
```

---

## Task 14: End-to-end integration

**Files:**
- Test: `tests/sdk/test_integration.py`

**Interfaces:**
- Consumes: the whole SDK + real modules through a real config.

- [ ] **Step 1: Write the integration test** (`tests/sdk/test_integration.py`)

```python
import json
from pathlib import Path

import trustable
from trustable.sdk.engine import SdkRuntime

CONFIG = """
project: itest
modules:
  audit:
    enabled: true
    log_level: silver
    sink_path: "{sink}"
  explainability:
    enabled: true
    capture_rag_context: true
"""


def test_decorated_call_produces_enriched_silver_record(tmp_path: Path):
    sink = tmp_path / "audit"
    cfg = tmp_path / "trustable.yaml"
    cfg.write_text(CONFIG.format(sink=str(sink).replace("\\", "/")))
    SdkRuntime.reset()

    @trustable.trace(managed=True, config_path=str(cfg))
    def answer(prompt: str) -> str:
        trustable.record(source_documents=[{"id": "d1", "score": 0.9, "content": "ctx"}])
        return "<thinking>reasoned</thinking>The answer."

    result = answer("why is the sky blue?")

    assert result == "The answer."  # managed mode stripped the reasoning
    silver = json.loads((sink / "silver.jsonl").read_text().strip().splitlines()[-1])
    assert silver["response"] == "The answer."
    assert silver["reasoning"] == "reasoned"
    assert silver["source_documents"][0]["id"] == "d1"
    SdkRuntime.reset()
```

- [ ] **Step 2: Run the integration test**

Run: `uv run pytest tests/sdk/test_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite + ruff + commit**

```bash
uv run pytest -q && uv run ruff check src tests
git add tests/sdk/test_integration.py
git commit -m "test(sdk): end-to-end audit + explainability through a decorated call"
```

---

## Final verification

- [ ] **Install with the extra and smoke-test the developer experience**

```bash
uv pip install -e ".[dev]"
uv run pytest -q
```
Expected: full suite green; `trustable modules list` now shows `audit` with `[Tracer]` and `explainability` with `[OutputGuard]` capabilities.

- [ ] **Confirm the base install stays OTel-free**

The audit import is lazy; `import trustable` and `trustable version` must work whether or not `[audit]` is installed. (Dev env has OTel, so this is a code-review check: `otel.py` is the only file importing `opentelemetry`, and it does so under `try/except`.)

---

## Acceptance criteria coverage (self-review)

1. `pip install -e ".[audit]"` exposes `trace`/`atrace`/`record`/`Blocked` → Tasks 1, 13.
2. `@trustable.trace` on sync + async `str->str` produces span + Silver record → Tasks 6, 7, 10, 14.
3. Escape hatches + `trace()`/`atrace()` context-managers → Tasks 5, 6, 7.
4. OTel span with `gen_ai.*` (InMemory) + Bronze/Silver JSONL per `log_level`; OTLP attachable → Tasks 8, 9, 10.
5. `audit` without `[audit]` extra → clear error at build time → Tasks 8, 10.
6. `trustable.record(source_documents=...)` → `rag_context` record in Silver → Tasks 2, 12, 14.
7. `<thinking>` extracted; managed strips, observe preserves → Tasks 11, 12, 6.
8. Throwing module fails open; `ctx.blocked` raises `Blocked` → Task 5 (+ Foundation pipeline).
9. Full suite passes; ruff clean → every task + Final verification.
