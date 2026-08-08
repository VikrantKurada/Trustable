# Product roadmap

[← Back to README](../README.md)

---

Roadmaps are usually works of fiction — a wish list with quarters stapled to it. This one tries to be the opposite: a dependency graph. The order isn't about what's exciting; it's about what has to exist before the next thing *can* exist. You build the foundation before the house, not because foundations are thrilling, but because the house falls down otherwise.

Everything is organized as six sub-projects. Each one produces working, testable software on its own — no half-built cathedrals.

## Status at a glance

| # | Sub-project | Status | Depends on |
| :-- | :--- | :--- | :--- |
| **1** | **Foundation** — config, plugin engine, runtime, CLI | ✅ **Shipped** | — |
| 2 | **SDK: Audit & Explainability** | ⏭️ **Next** | #1 |
| 3 | **Testing Harness** | 📋 Planned | #1, #2 |
| 4 | **Security Module** | 📋 Planned | #1, #2 |
| 5 | **Reviewability** — prompts-as-code + GitHub Action | 📋 Planned | #1 |
| 6 | **Integrations & CI/CD** — Docker, Actions, enterprise sinks | 📋 Planned | #1–#4 |

---

## 1. Foundation — ✅ Shipped

The engine everything else plugs into. Config parsing with two-pass validation, the capability-protocol plugin framework, three-source discovery, the fail-open runtime pipeline, and a working CLI (`init`, `validate`, `modules list/info`). Four built-in module stubs carry real, validated config schemas today; a reference module proves the whole framework end to end.

Forty-seven tests, reviewed task-by-task and once more across the whole branch. This is the part you can run right now.

## 2. SDK: Audit & Explainability — ⏭️ Next

The developer-facing wrapper that makes the engine reach your actual model calls. The headline is the `@trustable.trace` decorator — wrap your existing calling function and get the full request/response lifecycle captured: latency, tokens, raw payloads, via OpenTelemetry. Alongside it, the first real module behavior: explainability logging (which retrieved chunks produced this answer, and the model's extracted reasoning) and the Bronze/Silver/Gold sink structure to file it all in.

Why it's next: it's the shortest path from "the engine exists" to "a developer gets value in an afternoon." Auditing is the job teams reach for first, and it requires no changes to what the model does — just a wrapper around the call.

## 3. Testing Harness — 📋 Planned

The `trustable test` command and the machinery behind it: run a golden dataset through your model on every commit, score the outputs with a configurable second model (LLM-as-a-judge, local or remote), and enforce YAML-defined assertions that fail the CI build when breached. Depends on the SDK, because judging outputs means capturing them first.

## 4. Security Module — 📋 Planned

The real behavior behind the security config: PII and secret masking before input reaches the model, and injection scanning that rejects high-risk prompts outright. Built as guards on the same pipeline the SDK drives, which is why it comes after #2.

## 5. Reviewability — 📋 Planned

Prompts-as-code: the registry that pulls prompts into version-controlled files loaded by id and version, and the GitHub Action that comments on pull requests with a semantic diff of prompt changes. Depends only on the Foundation — it's largely dev-time tooling — so it can move in parallel with the runtime modules if there's appetite.

## 6. Integrations & CI/CD — 📋 Planned

The edges. A Dockerfile tuned to run inside a GitHub Actions workflow (and to exploit a beefy local box for heavy evaluation before CI), plus the real sink routes into enterprise platforms — Databricks, Unity Catalog governance on the medallion tiers. This is last because it integrates everything before it; there's no point routing audit logs to a lakehouse before the audit logs exist.

---

## How to read the order

Two honest notes.

First, **the order is dependency-driven, not marketing-driven.** Security is arguably the most *urgent* module for a nervous team, and it's #4, not #1 — because it's a guard on a pipeline that the SDK (#2) brings to life. Building it first would mean building it twice.

Second, **this is a near-term map, and near-term maps are the trustworthy kind.** For where the project points *after* the six sub-projects — the plugin ecosystem, the policy engine, the bigger bets — see [the long game](future.md). That page is honest about being speculative. This one tries hard not to be.

---

**Next:** [The long game →](future.md) · [The art of the possible →](art-of-the-possible.md)
