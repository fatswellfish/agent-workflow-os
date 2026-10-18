# 01 · Memory Architecture: Three Layers That Must Not Merge

> The single highest-leverage idea in this repo.
> If you only fix one thing, fix where volatile facts live.

---

## The symptom

You update a config value. You update the place you *think* it lives. A week later the agent
uses the old value, confidently, with no error. You check the file — it's correct. You're not
going crazy.

## The cause

An AI agent has several places it can "remember" things, and they are **loaded by completely
different mechanisms**. The mechanisms differ in three ways that matter:

| | Injected | Paid | Changes |
|---|---|---|---|
| **Memory** (always-on file) | Every turn | Every turn | Rarely — and it *should* be rarely |
| **Skills** (on-demand procedures) | On trigger | Per task | When the environment changes |
| **Knowledge base** (searchable docs) | On query | Per query | Constantly |

Now consider a fact like "the inference engine listens on port 8005".

- Its **change rate is high** (weekly, sometimes daily during setup).
- If it lives in **memory**, it gets injected 100× a day and *still* can't be updated
  retroactively — every conversation that started before the change holds the stale value.
- If it lives in the **knowledge base**, the agent only reads it when it searches, so it can
  never be "accidentally stale in context" — it's read fresh, or not at all.

**High change rate + high injection rate = permanent inconsistency.**

That is the whole story. Everything else in this document follows from it.

---

## The three layers, precisely

### Memory — "how to think"

**What belongs:**
- Behavioral rules that should hold in *every* session, regardless of task.
  ("Do not guess. Search the official docs first." / "Never fabricate output.")
- Pointers: "For anything about the deployment, read `skill:deployment-architecture`."
- Facts about the *user* that change on the scale of years.

**What does not:**
- Port numbers, file paths, model names, version strings, IP addresses
- Anything you changed in the last month
- Procedures ("first do X, then Y")

**Why the budget is small and should stay small:**
Context is zero-sum. Every token of always-on memory is a token not available for the actual
task, and long always-on context measurably degrades instruction-following
(*Lost in the Middle*, [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)).
A 2,000-character memory is not a limitation to work around — it is the design.

### Skills — "how to do"

**What belongs:**
- Step-by-step procedures that only matter for one kind of job
- Commands, scripts, exact syntax
- Pitfalls and their fixes
- Environment configuration that changes when the environment changes

**The key property:** a skill is **loaded lazily**. Its trigger description is always visible
(so the agent knows it exists), but its body costs nothing until it's needed.
This is Anthropic's *progressive disclosure* model — the mechanism that makes it viable to have
100+ skills without paying for 100+ documents every turn.

**What does not belong:**
- Facts about the world (that's the knowledge base)
- Rules that must apply when *no* skill is triggered (that's memory)

### Knowledge base — "what happened"

**What belongs:**
- Decisions and their rationale
- Project state and history
- Research and intelligence
- Anything you might need to *cite* rather than *execute*

**The key property:** it is not in context. The agent sees it only when it searches.
That's a feature: it can grow without bound, and stale entries can't leak into a turn that
didn't ask for them.

---

## The boundary rule (memorize this one line)

> **Memory = how to think · Skill = how to do · Knowledge base = what happened.**
>
> **Anything with a change rate faster than "months" does not go in memory.
> Memory holds pointers, not values.**

Decide in this order, first hit wins:

1. Does it constrain *how the agent behaves*, in a way that should hold regardless of task,
   and change roughly never? → **Memory**
2. Is it *the steps for doing one kind of thing*, needed only when doing that thing? → **Skill**
3. Is it *a fact, decision, or history* that should be quotable but not executable? →
   **Knowledge base**

If a piece of content seems to belong in two places, it belongs in one place and is
**referenced** from the other. See `04-verification.md` for how to enforce that.

---

## Failure modes, with mechanism

These are not hypothetical. Each one happened.

### 1. Volatile fact in memory
**Mechanism:** the file is re-read from disk each turn, but the *conversation* has already
absorbed the old value. Editing the file does not reach back into running context.
**Symptom:** correct file, wrong answer, no error.
**Fix:** the fact must live outside memory; memory holds a pointer.

### 2. Procedure in memory
**Mechanism:** procedures are long. They consume the scarce always-on budget, so real rules
get evicted to make room.
**Symptom:** the agent follows step-by-step instructions on a task that didn't need them,
while ignoring a rule that matters.
**Fix:** move to a skill.

### 3. Index pointing at a nonexistent target
**Mechanism:** skill indexes are plain text with no foreign-key constraint. A name written
"because there should be such a skill" is indistinguishable from one that exists.
**Symptom:** the agent tries to load it, fails, and **improvises** — producing plausible
output from general knowledge rather than erroring.
This is worse than a crash, because it produces confident wrong work.
**Fix:** a checker that resolves every index entry against the actual skill directory.
See `scripts/check.py`.

### 4. Same fact in three places
**Mechanism:** no declared ownership. Each place is edited independently when its author
notices it.
**Symptom:** contradictory values; no way to tell which is live without checking the system.
**Fix:** an ownership table — one declared home per fact class, everyone else references.

### 5. Skill content duplicated into the knowledge base
**Mechanism:** the knowledge base is not in context. Writing "the procedure is here" into a
document the agent never reads achieves nothing.
**Symptom:** two copies of the procedure drift apart; the skill copy wins in practice, the
knowledge-base copy rots silently.
**Fix:** the knowledge base holds *why* and *what*, skills hold *how*.

---

## How this maps to known frameworks

- **CoALA** ([arXiv:2309.02427](https://arxiv.org/abs/2309.02427)) splits agent memory into
  working / episodic / semantic / procedural. Our three layers are a deployment-oriented
  rendering of the same split: memory ≈ working + behavioral constraints, knowledge base ≈
  episodic + semantic, skills ≈ procedural.
- **MemGPT** ([arXiv:2310.08560](https://arxiv.org/abs/2310.08560)) frames the context window
  as RAM and external storage as disk, with paging. Skills are the page table.
- **Anthropic's** positioning of CLAUDE.md (always-on) vs Skills (progressive disclosure) vs
  MCP (tool connections) is the same three-way split, arrived at independently.

If your instinct is "this is obvious" — the architecture is obvious. Keeping it intact while
the system grows is not.

---

## Checklist

Before adding anything to memory, ask:

- [ ] Would this rule survive a total change of hardware, tools, and models? (No → skill)
- [ ] Does it contain a number, path, or name that could change? (Yes → knowledge base + pointer)
- [ ] Does it only matter for one category of task? (Yes → skill)
- [ ] Am I adding this because the agent forgot, or because it never had a place to look?

The last question is the important one. Most "the agent forgot" problems are actually
"there was no single place to look."
