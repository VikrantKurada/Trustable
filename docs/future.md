# The long game

[← Back to README](../README.md)

---

The [roadmap](roadmap.md) is a promise; this page is a set of guesses. It's worth keeping the two apart. What follows is where Trustable *points* once the six sub-projects exist — the bets that only make sense on top of a finished foundation, and that we'd be foolish to commit to dates for now. Read it as a direction, not a schedule.

The interesting thing about a plugin engine with a config-as-code control surface is that it's a platform whether or not you meant it to be. Once modules are small and the seams are real, a few large possibilities open up that weren't available to any single tool.

## 1. An ecosystem, not a product

The most important thing Trustable could become is a *substrate other people build on*. The architecture already supports third-party modules discovered from installed packages — which means the natural endpoint isn't five modules maintained by one team, it's a registry of them maintained by many. A `trustable-hipaa` module written by a healthcare team. A `trustable-finreg` written by someone who's read the regulations so you don't have to. A masking module tuned for a specific language.

The measure of success here is uncomfortable and clarifying: **the project has succeeded when most of the useful modules weren't written by us.** A tool becomes infrastructure at the moment its authors stop being the main source of its value.

## 2. Policy as code, and the compliance argument

Right now governance is expressed per-module. The larger idea is a single *policy* layer above them: one declarative document that says "in this repo, PII masking is mandatory, all model calls must be traced to Gold tier, and no prompt ships without a passing eval" — and a `trustable` command that *proves* the policy holds, in CI, as a gate.

That's the thing enterprises actually want and can't buy easily today: not a dashboard, but a *check* that turns a governance policy into a failing build. It's also the natural bridge to real compliance work — SOC 2, HIPAA, the EU AI Act — where the hard part isn't the controls, it's *demonstrating* the controls held. A tool whose whole design is config-as-code in the repo is unusually well-placed to generate that evidence as a byproduct of normal work.

## 3. Evaluation as a first-class, local, continuous thing

The local-first principle points somewhere specific. The reason to obsess over running heavy evaluation on a developer's own beefy box — an RTX-class GPU, lots of RAM — is that it makes *comprehensive* evaluation cheap enough to run continuously instead of occasionally. The long-game version of the testing module isn't "run a golden set in CI." It's a standing evaluation service: every prompt change scored across a battery of judges, adversarial inputs, and regression sets, locally, before the change ever leaves the laptop. Evals stop being a gate you dread and become a feedback loop you barely notice, like a type-checker.

## 4. The audit lake as a product surface

The medallion tiers (Bronze → Silver → Gold) are drawn as an implementation detail today. They're actually a seam to something bigger: once every interaction is landing in a structured, tiered store with lineage attached, that store is *queryable* in ways that feed back into the product. Which prompts drive the most retries? Which retrieved documents correlate with bad answers? Which users are probing for injections? The audit trail stops being a forensic tool you open after a disaster and becomes an analytics surface you build on.

## 5. Automation at the edges

The extensibility principle explicitly names workflow automation — `n8n`, webhooks, local orchestration. The long game is that Trustable becomes the *source of events* for an operational fabric around your LLM app: an injection attempt fires an alert, an eval regression opens a ticket, a spike in a masked-entity type pages the on-call. Governance stops being a report someone reads on Fridays and becomes a nervous system that reacts.

## The honest caveats

Two, stated plainly, because a future page without caveats is just marketing.

**These are options, not commitments.** Every one of them depends on the foundation being genuinely solid and the early modules being genuinely adopted. If sub-project #2 lands and nobody turns it on, none of this matters, and we should spend our time understanding why instead of building #5's dreams.

**The risk isn't ambition, it's dilution.** The failure mode for a tool like this is becoming a heavy platform that does ten things adequately and nothing indispensably. Every item above is only worth building if it can be built *without breaking the four principles* — opt-in, configurable, extendable, local-first. The day the policy engine requires a rewrite, or the audit lake requires a hosted service you can't run locally, the idea has drifted from the thing that made it worth using. The long game is played by holding the constraints, not relaxing them.

---

**Next:** [The art of the possible →](art-of-the-possible.md) · [Product roadmap →](roadmap.md)
