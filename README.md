# Agent Workflow OS

> A practical, battle-tested architecture for running AI agents as a real production system —
> not a prompt collection.

**English** | [中文](README.zh-CN.md)

---

## The problem

Most people use an AI agent like a very smart chat box. It works until it doesn't:

- You tell it something once, and next week it's gone.
- You correct it, and the correction leaks into things it shouldn't touch.
- It "remembers" a port number from three months ago and confidently uses the wrong one.
- Your instructions, your skills, and your notes each say something different — and nobody knows which is true.

This repo is the architecture that came out of hitting those walls, repeatedly, over months of
real use: a local DGX cluster, a media production pipeline, a software pipeline, and a family
archive — all driven by one agent.

It is not a framework. It is a **set of habits, boundaries, and one verification script** that
keep a large instruction system from rotting.

---

## Core idea: the agent has three kinds of memory, and they are not interchangeable

| Layer | What lives here | Loaded | Cost |
|---|---|---|---|
| **Memory** | How to *think*. Behavioral rules. | Every turn, always | Paid every turn |
| **Skills** | How to *do* a specific job. Procedures, scripts, pitfalls. | Only when triggered | Paid per task |
| **Knowledge base** | What *happened*. Facts, decisions, history. | Only when searched | Paid per query |

The rule that follows:

> **Memory stores "how to think", skills store "how to do", the knowledge base stores "what happened".**

And one hard constraint that resolves most consistency problems before they start:

> **Never put volatile facts (ports, paths, model names, versions) in memory.
> Memory only holds pointers to a single source of truth.**

Why: memory is injected every single turn. A fact with a high change rate living in a
high-injection channel is a disaster combination — you update the file, but every
already-running conversation still holds the old value, and the user has no reason to restart.

This is the same architectural split the industry converged on independently
(see [CoALA](https://arxiv.org/abs/2309.02427): working / episodic / semantic / procedural memory),
and it maps cleanly onto how Claude Skills, CLAUDE.md, and MCP divide responsibilities.

📖 Full rationale → [`docs/01-memory-architecture.md`](docs/01-memory-architecture.md)

---

## Core idea 2: indexes are pointers, and pointers rot

A common failure: an index file says "for this task, load `media-pipeline`" — but
`media-pipeline` was never created, or was renamed two months ago.

The dangerous part is not that it fails. It's that **it fails silently**: the agent can't load
the skill, so it improvises from general knowledge, and the output looks fine.

We found **27 such dead links across 7 index skills** in one audit.

The fix is not discipline. It's a script:

```bash
python scripts/check.py
```

It fails the build if any index points at a skill that doesn't exist. Same idea for port
numbers, model names, and memory size:

📖 [`docs/04-verification.md`](docs/04-verification.md) · [`scripts/check.py`](scripts/check.py)

---

## Core idea 3: determinism is free, reasoning is not

> Mechanical tasks → scripts. Subjective analysis → the model.

Validating that a skill's referenced name exists, that a port in a doc matches the deployment
ledger, that a filename follows the convention — these are **deterministic checks**.
Doing them with an LLM costs tokens and introduces variance. Doing them in Python costs nothing
and never gets tired.

Red Hat's AI engineering team measured a **26% cost reduction** from exactly this split.
In our case it's not about cost — it's that a script cannot "forget" to run the check.

---

## What's in here

```
docs/           The thinking. Read in order.
  01-memory-architecture.md   Three-layer memory, why they can't merge
  02-routing.md               One entry point, indexes as pointers
  03-pipeline-design.md       Work domains, roles, engine switching
  04-verification.md          Consistency gates that run themselves
skills/         De-identified skill templates, ready to adapt
scripts/        The verification tooling (real, runnable)
examples/       Worked examples with all identifying data removed
```

### Start here if you have 5 minutes

1. [`docs/01-memory-architecture.md`](docs/01-memory-architecture.md) — the one idea that fixes most of it
2. [`scripts/check.py`](scripts/check.py) — the one tool that keeps it fixed

---

## Who this is for

- You run one agent across several genuinely different jobs (writing, coding, media, ops)
  and the instruction surface has grown past the point where you can hold it in your head.
- You've already been bitten by the agent confidently using a stale fact.
- You're considering splitting one agent into several specialized ones — and want to know
  whether that's actually the right move (spoiler: often it isn't; see `docs/03`).

## Who this is *not* for

- Single-purpose agents. The overhead doesn't pay for itself.
- Teams without a shared source of truth for config. Fix that first.

---

## Status

Extracted from a working system, not written in the abstract. Everything in `scripts/` runs.
Everything in `docs/` describes a choice that was made after a failure, and says what the
failure was.

Actively maintained as the underlying system evolves — structure may change, the principles
shouldn't.

---

## Contributing

Issues and PRs welcome. This repo is deliberately opinionated; disagreement is more useful
than agreement. If something here broke for you, that's the most valuable kind of issue.

## License

Not yet decided. Until a license is added, all rights are reserved — but you are welcome to
read, learn from, and adapt the ideas.
