# Why Trustable exists

[← Back to README](../README.md)

---

Here's a thing that should bother you more than it does. We spent forty years learning how to keep software honest — types, tests, code review, version control, logging, static analysis — and then we bolted a large language model onto the side of the app and quietly agreed that none of it applies to that part.

It doesn't apply because the model breaks all the assumptions the tools were built on.

Take code review. The whole point of a pull request is that a diff is legible: you can look at the two versions of a function and reason about how the behavior changed. Now change a prompt. The diff is a paragraph of English, and the "behavior" isn't a return value, it's a probability distribution over every possible sentence. Two reviewers can stare at the same three-word change and have no idea whether it made the product better or worse. So in practice nobody reviews prompt changes. They get typed straight into production by whoever's closest, which is exactly the workflow we spent decades teaching ourselves not to use.

Take testing. Tests work because behavior is deterministic: same input, same output, `assertEqual`. Ask a model the same question twice and you get two different answers, both plausibly fine. String matching is useless. So teams either don't test the model at all, or they write brittle checks that break on paraphrase and get deleted within a month.

Take logging. When ordinary software misbehaves, you read the log and see what happened. When an LLM app misbehaves, the interesting question is *what did the model actually see* — the full prompt, the retrieved documents, the system message, the tool outputs — and almost nobody writes that down. So the postmortem for "why did it say that?" is a shrug.

And then there's the new category of failure that has no analogue in normal software: the input is also an instruction. A user — or a document your app retrieved, or an email it read — can hide a command in the text, and the model, being agreeable, may follow it. We have a forty-year-old discipline for "don't trust user input" and almost none of it has been ported to the case where untrusted input and trusted instructions are the same string.

## The tempting wrong answers

There are two obvious responses, and both are worse than they look.

**The first is to do nothing** and promise you'll add governance "when we're bigger." This feels prudent and is not. Governance added late is a rewrite: by the time you care about audit trails, the model calls are scattered through fifty files, each done slightly differently, and there's no single place to add a hook. The cost of instrumenting an LLM app grows super-linearly with its age. The cheapest time to add a seatbelt is before the crash, which is to say now, when it's annoying and seems unnecessary.

**The second is to adopt a framework** that promises to do it all — rebuild your app "the right way" on top of some opinionated platform. But rewrites are how startups die, and the teams who most need governance are precisely the ones who can least afford to stop shipping features for a quarter to re-platform. A tool that demands a rewrite as the price of admission will be admired and not used.

## The actual answer: an overlay

So the constraint is sharp. Whatever fixes this has to (a) require no rewrite, (b) let you adopt it one piece at a time, and (c) get out of the way — including failing open, so a bug in your *governance* never takes down your *product*.

That's a strange shape for a tool, and it's the shape of Trustable. You add a `trustable.yaml` to the repo and switch on the modules you want. The prompts move into version-controlled files so a diff means something. A test harness scores *semantics* instead of strings, using a second model as a judge. Every model call gets wrapped in a structured trace so the log finally contains what the model saw. Inputs get scanned for injection and scrubbed of secrets before they reach the API. And the retrieved context that produced an answer gets recorded next to the answer, so "why did it say that?" has a real reply.

Crucially, each of those is independent. You can adopt auditing without touching security. You can run the whole thing on your laptop before it ever reaches CI. And if any of it throws, the guardrail is skipped and your app proceeds — because a governance layer that can crash production is a governance layer nobody will turn on.

## Why "as code"

One more decision worth defending: everything is configuration-as-code, checked into the same repo as the app. That's not an aesthetic preference. It's what makes the whole thing reviewable and auditable in tools you already have. Your policy for what counts as sensitive, which model judges your outputs, where audit logs go — those become diffs in pull requests, reverted by `git revert`, and explained by `git blame`. Governance you can't review is just a rumor. Trustable turns it into text.

That's the bet. Not a new platform. A thin, honest layer that makes the tools you already trust reach the one part of your app they couldn't.

---

**Next:** [What's in the box →](features.md) · [The Product Manager's view →](product-manager.md)
