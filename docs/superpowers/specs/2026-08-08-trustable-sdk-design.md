# Trustable — SDK: Audit & Explainability (Sub-project #2) Design

**Date:** 2026-08-08
**Status:** Approved (design), pending implementation plan
**Depends on:** Sub-project #1 (the Foundation) — shipped
**Source PRD:** [`Trustable_PRD_v1.md`](../../../Trustable_PRD_v1.md) · [Foundation design](2026-08-07-trustable-foundation-design.md)

---

## 1. Context

Sub-project #2 builds the **developer-facing SDK** that makes the Foundation's runtime reach a live model call, plus the first two real modules — **Audit** and **Explainability** — that today ship as no-capability stubs.

The Foundation already provides the substrate this builds on:
- `InteractionContext(prompt, response, metadata, records, blocked, block_reason)` — threaded through the pipeline.
- `Pipeline` with `run_input_guards(ctx)`, `run_output_guards(ctx)`, and `trace(ctx)` (a context manager: `start_trace` on enter, `end_trace` on exit, reversed).
- `TrustableRuntime.from_config(config, module_configs, registry)`.
- Capability protocols `InputGuard`, `OutputGuard`, `Tracer`, `CommandProvider`.
- `AuditConfig(enabled, sink="local", log_level: bronze|silver|gold="silver")` and `ExplainabilityConfig(enabled, capture_rag_context=False)`, registered today via `_stub_spec` in `modules/builtins.py`.

### Decisions locked in during brainstorming

- **Scope: OTel as the backbone.** OpenTelemetry is the actual tracing layer (real spans + exporters), not just a seam. Medallion sinks are implemented as custom OTel span exporters.
- **Decorator DX: convention + escape hatches on a context-manager.** A default extraction convention that works for the common `str -> str` shape, overridable with explicit `prompt=`/`response=` extractors, all built on a public `trace()` / `atrace()` context-manager.
- **Sync and async both.** `@trustable.trace` auto-detects `async def`; `atrace()` is the async context-manager.
- **Response policy: observe by default, managed opt-in** (§4).

### Deferred (out of scope for #2)

- **Auto-instrumentation** (monkeypatching OpenAI/LangChain/LiteLLM) — fragile, large; the decorator covers the 90% case first.
- **Enterprise sinks** (Databricks / Unity Catalog) — sub-project #6.
- **Gold-tier aggregation** — analytics work; the tier is a logged no-op for now.

---

## 2. Goals & non-goals

**Goals (this sub-project delivers):**
- `trustable.trace` / `atrace` context-managers and a `@trustable.trace` decorator (sync + async) that drive the pipeline around a real model call.
- Prompt/response extraction: convention + callable/param-name escape hatches.
- `trustable.record(...)` (contextvar-based) and the `trustable.Blocked` exception.
- A real **Audit** `Tracer`: OTel span per interaction with `gen_ai.*` attributes, exported to local **Bronze/Silver** medallion sinks (JSONL); interoperable with any standard OTLP exporter.
- A real **Explainability** `OutputGuard`: RAG-context lineage and `<thinking>` chain-of-thought extraction, enriching `ctx.records`.
- Comprehensive local (no-network) tests.

**Non-goals:** auto-instrumentation, enterprise sinks, Gold aggregation, real Security/Test module behavior (later sub-projects), any change to the plugin engine's design.

---

## 3. Architecture & call flow

**`SdkRuntime`** (`sdk/engine.py`) loads `trustable.yaml` once, builds a `TrustableRuntime`, and **caches it** (module-level, keyed by resolved config path) so every traced call reuses the same assembled pipeline and the same global OTel `TracerProvider`. A `reset()` hook clears the cache for tests.

Flow for one traced interaction:

```
   build InteractionContext(prompt = extracted from the call)
          │
   run_input_guards(ctx)            # no-op in #2; Security plugs in here at #4
          │
   ctx.blocked?  ── yes ──►  raise trustable.Blocked(ctx.block_reason)
          │ no
   with pipeline.trace(ctx):        # Audit.start_trace(): open an OTel span
          ├─ result = fn(*args, **kwargs)          # the real model call
          ├─ ctx.response = extract_response(result)
          └─ run_output_guards(ctx)                # Explainability: enrich ctx.records
   « exit »                         # Audit.end_trace(): set attributes, close span,
          │                           export span → medallion sinks
   return  result  (observe)  |  ctx.response  (managed)     # see §4
```

Two invariants inherited from the Foundation:
- **Cross-module cooperation is via the shared `InteractionContext`.** Explainability (`OutputGuard`, priority 20) runs *inside* the trace block and appends to `ctx.records`; Audit (`Tracer`, priority 30) persists those records on `end_trace`. Neither module references the other. Consequence: explainability *enriches*, audit *persists*; records reach disk only when audit is also enabled.
- **`run_output_guards` runs inside the trace block**, so the span captures the enriched context.

Everything stays **fail-open**: the pipeline wraps every module call, so a broken exporter or throwing guard is logged and skipped — the model call and its result survive. The lone deliberate stop is `ctx.blocked`, surfaced as the typed `Blocked` exception.

---

## 4. Developer API surface

Exposed from the package root (`import trustable`). Three shapes, one primitive.

**1. Decorator, convention default:**
```python
@trustable.trace
def answer(prompt: str) -> str:
    return openai_call(prompt)
```
Convention: prompt from a param named `prompt` or `messages`, else the first positional arg; response = return value.

**2. Decorator, escape hatches:**
```python
@trustable.trace(
    name="summarize",
    prompt=lambda *a, **k: k["messages"],            # callable OR a param-name string
    response=lambda r: r.choices[0].message.content,
)
def summarize(*, messages): ...
```
`prompt=`/`response=` accept a callable or a param-name `str`; anything not overridden falls back to convention.

**3. Context-manager, full control (the primitive the decorator wraps):**
```python
with trustable.trace(prompt=messages, name="chat") as ctx:   # input guards run on enter
    resp = openai_call(messages)
    ctx.response = resp.choices[0].message.content
# on exit: output guards + end-of-span + export
answer = ctx.response   # possibly guard-modified
```

**Async** mirrors all three: `@trustable.trace` on an `async def` returns an async wrapper; `async with trustable.atrace(...) as ctx:` is the async context-manager.

**Helpers:**
- `trustable.record(source_documents=[...], **fields)` — called *inside* a traced function; finds the active interaction via a `contextvar` and attaches data to `ctx.metadata`. This is how Explainability receives RAG chunks without the developer threading `ctx`.
- `trustable.Blocked` — typed exception raised when an input guard sets `ctx.blocked` (dormant in #2).

### Response policy — observe by default, managed opt-in

Output guards can modify `ctx.response` (Explainability strips `<thinking>`). What the traced call returns:
- **Observe (default):** returns exactly what the wrapped function returned. Guard mutations land in the span and Silver log, never silently altering app data.
- **Managed** (`@trustable.trace(managed=True)` / `trace(managed=True)`): returns `ctx.response` (the guard-modified string), so stripping/redaction reaches the caller. Opt-in because re-injecting a cleaned string only makes sense when the response *is* that string; complex return objects are returned unchanged regardless.

---

## 5. The Audit module (`modules/audit/`)

A real `Tracer` (priority 30) replacing the stub. Where "OTel as the backbone" lives.

**Spans.** `start_trace(ctx)` opens an OTel span; `end_trace(ctx)` sets attributes and closes it. Attributes follow the emerging **`gen_ai.*` semantic conventions**:

| Attribute | Source |
|---|---|
| span name, `gen_ai.operation.name` | `name=` (or wrapped function name) |
| `gen_ai.request.model` / `gen_ai.response.model` | `ctx.metadata` (developer/adapter-supplied) |
| `gen_ai.usage.input_tokens` / `output_tokens` | `ctx.metadata` if present |
| latency | span start/end timing |
| `trustable.records` (count), `trustable.blocked` | `ctx.records`, `ctx.blocked` |

Full prompt/response **payloads are not forced onto span attributes** (size limits, backend pollution). They live in the sink records, and optionally attach as span **events** behind `capture_payloads_as_events` (default off).

**TracerProvider & sinks.** On first use the module configures a global `TracerProvider` with a custom `SpanProcessor` that fans finished spans out to the enabled medallion **SpanExporters**:
- **Bronze** — raw span (all attributes/events + full payload) as JSONL; the forensic record.
- **Silver** — a cleaned, flattened record `{id, ts, name, model, prompt, response, tokens, latency_ms, source_documents, reasoning, ...}`, pulling from `ctx` including Explainability's `ctx.records`; the queryable record.
- **Gold** — deferred; a logged no-op if selected.

`log_level` selects the highest tier written: `bronze` → Bronze; `silver` → Bronze + Silver; `gold` → + Gold (no-op).

Because the sinks are ordinary OTel exporters, a developer adds a standard OTLP exporter alongside ours to ship traces to Jaeger/Grafana/Honeycomb — a documented one-liner, not something we build. That interoperability is the OTel bet's payoff.

**Dependency.** `opentelemetry-api` + `opentelemetry-sdk` ship as the optional extra `trustable[audit]`, imported lazily inside `modules/audit/` (never at package import). If `audit` is enabled without the extra, the module raises a **clear, actionable error when the runtime is built** (fail-loud on a setup problem).

---

## 6. The Explainability module (`modules/explainability/`)

A real `OutputGuard` (priority 20) replacing the stub. Runs just before Audit's `end_trace`; both jobs enrich `ctx.records` so Audit's Silver tier persists them.

**1. RAG context lineage.** When the developer calls `trustable.record(source_documents=[...])`, the chunks land on `ctx.metadata`. On `check_output(ctx)`, if `capture_rag_context` is on, the module normalizes them into:
```python
{"type": "rag_context",
 "source_documents": [{"id": "doc-42", "score": 0.87, "content": "…", "metadata": {...}}, ...]}
```
A small normalizer accepts LangChain `Document` objects, dicts, and `(text, score)` tuples, and degrades gracefully (records what it can, never throws) on unexpected shapes.

**2. Chain-of-thought extraction.** If `ctx.response` is text, the module extracts a reasoning block — `<thinking>…</thinking>` by default — into:
```python
{"type": "reasoning", "content": "…extracted chain-of-thought…"}
```
and, in **managed mode**, strips it from `ctx.response` (the "hidden data object"); in observe mode it records without altering the return (§4).

**Config additions** (`ExplainabilityConfig`, additive with defaults):
- `capture_rag_context: bool = false` *(exists)*
- `extract_reasoning: bool = true`
- `reasoning_tag: str = "thinking"`
- `strip_reasoning: bool = true` (takes effect only in managed mode)

---

## 7. Config schema changes

Additive, backward-compatible (modules own their schemas; the Foundation's two-pass validation still applies):

- **`AuditConfig`** gains `sink_path: str = ".trustable/audit"` and `capture_payloads_as_events: bool = false`. Existing `sink`, `log_level` unchanged.
- **`ExplainabilityConfig`** gains `extract_reasoning`, `reasoning_tag`, `strip_reasoning` (see §6).
- `modules/builtins.py`: `audit` and `explainability` repointed from `_stub_spec(...)` to the real `audit_spec()` / `explainability_spec()`. Security and test remain stubs.

---

## 8. Package layout & dependencies

```
src/trustable/
├── sdk/
│   ├── __init__.py
│   ├── engine.py          # SdkRuntime: cached config→runtime, drives a traced call
│   ├── trace.py           # trace()/atrace() context-managers + @trace decorator (sync+async)
│   ├── extract.py         # prompt/response extraction (convention + callable/param-name)
│   └── current.py         # contextvar for the active ctx; trustable.record()
├── modules/
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── module.py      # AuditModule(Tracer) + audit_spec()
│   │   ├── otel.py        # TracerProvider setup, gen_ai attribute mapping
│   │   └── sinks.py       # medallion SpanExporters (Bronze/Silver JSONL)
│   └── explainability/
│       ├── __init__.py
│       ├── module.py      # ExplainabilityModule(OutputGuard) + explainability_spec()
│       └── rag.py         # source-document normalizer + CoT extraction
└── (config/schema.py, modules/builtins.py, __init__.py  ← edited)
```

**`pyproject.toml`:**
```toml
[project.optional-dependencies]
audit = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]
dev = ["pytest>=8.0", "ruff>=0.5", "opentelemetry-sdk>=1.20"]   # sdk added so audit tests run
```
Base install stays lean; OTel imported lazily inside `modules/audit/` only.

**`__init__.py`** gains public exports: `trace`, `atrace`, `record`, `Blocked` (existing exports retained).

---

## 9. Error handling

Consistent with the Foundation's asymmetry:
- **Runtime → fail-open.** The pipeline guards each module; a throwing exporter, a malformed RAG doc, a missing token count — logged and skipped, the call proceeds and returns.
- **Setup → fail-loud.** `audit` enabled without the `[audit]` extra raises a clear, actionable error at runtime-build time. Malformed config is already caught by two-pass validation.
- **`Blocked`** is the one deliberate control-flow exception (dormant in #2).

---

## 10. Testing strategy (pytest, no network)

- **Extraction** — convention (positional, `prompt`/`messages` kwarg) + both escape hatches (callable, param-name); sync and async.
- **Trace flow** — fake `fn`; input→call→output-guard→end ordering; `ctx.blocked` → `Blocked`; fail-open when a module throws.
- **Audit** — OTel `InMemorySpanExporter` asserts span name + `gen_ai.*` attributes; Bronze/Silver JSONL contain expected records per `log_level`; missing-extra error asserted. (`opentelemetry-sdk` added to dev deps.)
- **Explainability** — normalizer across Document/dict/tuple shapes; `<thinking>` extraction + managed-mode stripping vs observe-mode preservation; graceful degradation on junk.
- **Async** — async decorator and `atrace` end-to-end.
- **Integration** — a decorated function with audit + explainability both enabled, driven through a real assembled runtime, asserting a Silver record containing response, tokens, `source_documents`, and extracted `reasoning`.

---

## 11. Acceptance criteria

1. `pip install -e ".[audit]"` exposes `trustable.trace`, `atrace`, `record`, `Blocked` from the package root.
2. `@trustable.trace` traces a sync **and** an async `str -> str` function with zero extra config, producing a span and a Silver record.
3. Escape hatches (`prompt=`/`response=` as callable or param-name) and the `trace()`/`atrace()` context-managers all work.
4. Audit produces an OTel span with `gen_ai.*` attributes (verified via `InMemorySpanExporter`) and writes Bronze/Silver JSONL honoring `log_level`; a standard OTLP exporter can be attached alongside.
5. `audit` enabled without the `[audit]` extra raises a clear, actionable error at runtime-build time.
6. `trustable.record(source_documents=[...])` inside a traced function yields a `rag_context` record with `source_documents` + scores in the Silver log.
7. `<thinking>` reasoning is extracted into a `reasoning` record; managed mode strips it from the returned string, observe mode leaves the return untouched.
8. A throwing exporter or guard does not break the traced call (fail-open); `ctx.blocked` raises `Blocked`.
9. Full suite passes; ruff clean.

---

## 12. Out of scope (future sub-projects)

Auto-instrumentation of LLM libraries; enterprise sinks (Databricks/Unity Catalog, #6); Gold-tier aggregation; real Security (#4) and Testing (#3) module behavior; prompts-as-code / Reviewability (#5).
