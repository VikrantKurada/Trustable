# The Product Manager's view

[← Back to README](../README.md)

---

Most product documents open with a market size. This one opens with a confession: the market for "LLM governance" as a thing people go shopping for barely exists yet. Nobody wakes up wanting governance. They wake up wanting to ship a feature that talks to a model without it embarrassing them. Trustable's job is to be the thing they reach for in that moment — and to still be there, quietly useful, when the embarrassing thing eventually happens.

So let's talk about that job.

## Who it's for

Not the enterprise with a fifty-person platform team. They'll build their own, or buy something with a sales engineer attached. Trustable is for the team one or two steps earlier: **the early-stage company or team that has an LLM feature in production, or about to be, and a growing itch that they can't see, test, or defend what it's doing.** Small enough to move fast, big enough that a bad model output is now a real cost — a leaked customer email, a hallucinated refund policy, an injection that made the support bot promise a competitor's product.

These teams have three things in common. They already have a repo and a CI pipeline they trust. They cannot afford to stop shipping to re-platform. And they have exactly zero appetite for a tool that adds a second thing that can page them at 3 a.m. Every design choice in Trustable falls out of those three facts.

## The job it does

Borrow the "job to be done" framing and it gets clear. The customer isn't hiring Trustable to "govern their AI." They're hiring it to do one of these:

- *"Let me change a prompt without it being a coin flip."* → **Reviewability + Testability.**
- *"Let me sleep, knowing a stranger can't talk my bot into doing something dumb."* → **Security.**
- *"When something goes wrong, let me find out what actually happened."* → **Auditability.**
- *"Let me tell a customer — or a regulator — why the model said what it said."* → **Explainability.**

Notice these are separable jobs, hired at different moments. That's not an accident; it's the wedge.

## The wedge, and why it's opt-in

The trap for a tool like this is to show up as a five-module suite and ask for a big yes. Big yeses are rare and slow. So Trustable is built to be adopted on the strength of *one* job. A team adds `trustable.yaml`, turns on **only** audit tracing because they got burned once, and gets value in an afternoon. Later, a security scare turns on the injection guard. Later still, a flaky prompt turns on the eval harness. Each step is a small yes, reversible, low-risk.

This is why "opt-in" and "fail-open" aren't just engineering principles — they're the go-to-market. A tool you can turn on for one thing, that can't hurt you if it breaks, is a tool people will actually try. Adoption is the whole game, and adoption is a function of how small the first yes can be.

## Positioning: where Trustable sits

It's easy to confuse Trustable with its neighbors, so here's the honest map:

- **It is not an observability vendor** (LangSmith, Langfuse, Arize). Those are dashboards you send data *to*. Trustable is an overlay that lives *in your repo*, config-as-code, and can route *into* those platforms. It's upstream of the dashboard.
- **It is not an eval framework** (promptfoo, DeepEval). Testability overlaps, but Trustable's evals are one module among five, sharing config and plumbing with your security and audit story rather than living in a separate tool.
- **It is not a guardrails library** (Guardrails AI, NeMo). Security overlaps, but again — one module, same engine, same file.

The one-liner: **the others are point solutions you integrate; Trustable is the thin, opt-in layer that unifies them under one config and one plugin engine, in the repo you already have.** Its moat isn't any single module — each of those has a strong standalone competitor. Its moat is being the *coherent, local-first, no-rewrite substrate* they all plug into.

## How we'll know it worked

Vanity metrics for a dev tool are a trap. The numbers that would actually tell us Trustable is working:

1. **Time-to-first-value.** From `git clone` to a module doing something real, measured in minutes. If it's a day, we've failed.
2. **Modules-per-project over time.** The opt-in bet is that adoption *widens* — teams that start with one module turn on a second. If that curve is flat, the wedge isn't real.
3. **Survival of `trustable.yaml` in the repo.** The cruelest, truest metric: three months later, is it still there and still enabled, or was it quietly deleted? A governance tool that gets deleted was theater.
4. **Plugins written by people who aren't us.** The extensibility bet pays off only if outsiders build modules. First third-party plugin is a bigger milestone than any internal feature.

## The non-goals

Good products are defined as much by their refusals. Trustable is deliberately **not**:

- **A model or an inference provider.** It sits beside your model call; it never replaces it.
- **A rewrite.** The day it requires you to restructure your app is the day it's lost.
- **A hosted SaaS you send your data to.** Local-first is the default; the cloud is an opt-in sink, not the product.
- **A compliance certificate.** It gives you the record and the controls to *make* a compliance argument. It doesn't sign the form.

Hold those refusals and Trustable stays the thing it's trying to be: small, trusted, and turned on. Break them and it becomes one more heavy platform nobody has time for.

---

**Next:** [Product roadmap →](roadmap.md) · [The long game →](future.md) · [The art of the possible →](art-of-the-possible.md)
