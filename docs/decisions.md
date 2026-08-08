# Key decisions

[← Back to README](../README.md)

---

A design is really just a stack of decisions, and most of them are invisible by the time you see the result — which is a shame, because the decisions are the interesting part. Anyone can read the code and see *what* was built. This page is the *why*: the forks in the road, the option we didn't take, and what it would cost us if we were wrong.

Each entry is deliberately in the same shape: the fork, the call, the road not taken, the consequence.

---

## 1. Decompose the whole thing into sub-projects

**The fork.** The original spec described five feature modules plus a CLI, an SDK, and CI tooling — a platform. We could have designed it all at once.

**The call.** We didn't. We cut it into six sub-projects and built the *foundation* first, alone, to production quality. Only then does anything else get built.

**The road not taken.** Designing the whole platform in one spec. It would have produced a document too big to hold in your head and an implementation too big to review.

**The consequence.** Slower to a flashy demo, faster to a system that actually holds together. Each sub-project produces working, testable software on its own. If we're wrong, we discover it after one sub-project, not after the whole thing is entangled.

## 2. Build the full plugin framework *now*

**The fork.** For the foundation, how much of the extensibility machinery to build up front: just the internal seams, the whole thing, or nothing yet.

**The call.** The whole thing — a real registry, capability protocols, and three-source discovery including third-party packages — on day one.

**The road not taken.** "Seams now, plugins later." Tempting, and usually the right YAGNI answer. We overrode it here for one reason: extensibility is the *product*, not a feature of it. A plugin system retrofitted onto a system that grew up monolithic is never quite as clean as one designed in from the start.

**The consequence.** A heavier foundation, justified by the fact that the modules built on top of it are now genuinely small. The bet is that we'll write many modules and few engines. If that's false — if we only ever have five modules and no outsiders write any — we over-built. We think it's true.

## 3. Capability protocols + a pipeline, not an event bus

**The fork.** How modules attach and run. Three real candidates: typed capability interfaces composed into an ordered pipeline; a decoupled publish/subscribe event bus; or one fat base class every module extends.

**The call.** Capability protocols (`InputGuard`, `OutputGuard`, `Tracer`, `CommandProvider`) run through an explicit, priority-ordered, fail-open pipeline.

**The road not taken.** The event bus. It's the more fashionable, more "decoupled" choice — and the wrong one here. Guardrails need to run in a deterministic order and, sometimes, to *block synchronously*. Expressing "reject this request before it hits the model" in pub-sub means simulating synchronous control flow on top of an asynchronous abstraction, which is where debuggability goes to die. The monolithic base class we rejected for the opposite reason: it forces every module to carry hook methods it doesn't use.

**The consequence.** The set of extension points is fixed until we add a new capability to the core. That's a real constraint. We accept it because the extension points LLM guardrails need are, so far, few and well understood, and because typed capabilities make a module self-documenting.

## 4. A thin config core; modules own their schemas

**The fork.** Where the validation logic for each module's config lives. In one big schema in the core, or distributed to the modules.

**The call.** Two-pass validation. The core validates the envelope; each module validates its own block against its own registered schema. The core has never heard of `pii_masking` or `log_level`.

**The road not taken.** A monolithic config schema in the core that knows every module's fields. Simpler to write on the first day, and a millstone forever after — every new module would mean editing the core.

**The consequence.** A third-party plugin gets the same precise, friendly error messages as a built-in, with no core changes. The cost is a slightly more involved loader (two passes, a registry lookup between them). Cheap, and paid once.

## 5. Fail-open at runtime, fail-loud at config-time

**The fork.** What happens when something goes wrong — and it's genuinely two different questions for two different moments.

**The call.** At *runtime*, fail open: a module that throws is logged and skipped, the app proceeds; the only deliberate stop is a security block. At *config-time*, fail loud: precise errors, non-zero exit, nothing broken reaches production silently.

**The road not taken.** Failing closed at runtime — if a guard errors, block the request. Safer-sounding, and adoption poison. A governance layer that can take down your product by having a bug is a layer you leave turned off.

**The consequence.** This asymmetry is the single most important decision for whether anyone adopts the tool. It's why "fail-open" is treated as a load-bearing wall in the code, not a stray `try/except`.

## 6. Boring, sharp tools

**The fork.** The stack.

**The call.** Python 3.11+, Typer for the CLI, Pydantic v2 for config and validation, PyYAML, `uv` for environments, `hatchling` to build. Nothing exotic.

**The road not taken.** Anything clever. There was no reason to reach for it, and clever infrastructure is a tax you pay forever.

**The consequence.** Pydantic gives us strict, friendly validation almost for free; Typer gives a clean CLI that modules can extend; `uv` keeps environments fast and reproducible. The stack is deliberately unremarkable so the *design* can be the interesting part.

## 7. Reproducible by default — even the linter

**The fork.** A small one, discovered during the build: the code was being linted clean against a broad rule set that lived only in a developer's *machine*, not the repo. On a fresh clone, CI would lint against almost nothing.

**The call.** Pin the lint rules explicitly in `pyproject.toml`, and commit the lock file. Clean-lint should mean the same thing on every machine.

**The road not taken.** Shrugging. "It's green on my box" is the beginning of every reproducibility bug.

**The consequence.** Trivial to fix, easy to ignore, and worth flagging here because it's the whole ethos in miniature: a tool whose entire pitch is *make things you can trust and verify* has no business relying on state that isn't in the repo.

## 8. Test-first, reviewed every step

**The fork.** How to actually build it.

**The call.** Test-driven, one small task at a time, each task independently reviewed for both spec-compliance and quality before the next began, and the whole branch reviewed again at the end.

**The road not taken.** Building fast and reviewing once at the end — which is how you get a demo that works and a codebase nobody can change.

**The consequence.** Forty-seven tests, a clean history where every commit is green, and a final review that caught real gaps (a missing feature in one CLI command, the linter reproducibility hole above) while they were still cheap. Slower per step, faster to something trustworthy — which, for *this* project, is the only kind of fast that counts.

---

**Next:** [How it's built →](architecture.md) · [Product roadmap →](roadmap.md)
