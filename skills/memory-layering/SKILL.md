---
name: memory-layering
description: "Use when 决定一条内容放memory/skill/知识库哪一层，或发现记忆互相矛盾时。"
---

# Memory Layering

> Decide *where* a piece of knowledge belongs before writing it anywhere.
> Getting this wrong is the root cause of most "the agent forgot" and "the agent contradicts
> itself" problems.

## When to Use

- About to add something to always-on memory
- The agent used a stale fact
- Two documents disagree about the same thing
- Considering merging or splitting memory files

## The rule

> **Memory = how to think · Skill = how to do · Knowledge base = what happened.**
>
> **Anything with a change rate faster than "months" does not go in memory.
> Memory holds pointers, not values.**

## Decision procedure (first hit wins)

1. Does it constrain *behavior*, in a way that holds regardless of task, and changes roughly
   never?
   → **Memory**

2. Is it *the steps for doing one kind of thing*, needed only when doing that thing?
   → **Skill**

3. Is it *a fact, decision, or history* that should be quotable but not executable?
   → **Knowledge base**

If it seems to belong in two places: it belongs in one, and is **referenced** from the other.

## The test for a volatile fact

Ask: *"If this changes tomorrow, who needs to know?"*

- The answer is "every conversation in flight" → **it must not be in memory**.
  Memory is re-read from disk each turn, but a running conversation has already absorbed the
  old value. Editing the file does not reach back into context.
- The answer is "whoever does that kind of work next" → **skill**.
- The answer is "whoever looks it up" → **knowledge base**.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Port numbers / paths / model names in memory | High change rate × high injection rate = permanent inconsistency |
| Step-by-step procedures in memory | Consumes the scarce always-on budget; real rules get evicted |
| Index entries pointing at nonexistent skills | Fails silently — the agent improvises instead of erroring |
| The same procedure in both a skill and a doc | The doc is never read; the two drift; the doc rots |
| "Just put it everywhere so it's definitely there" | Guarantees contradiction, and nobody can tell which copy is live |

## Pointers, not copies

When memory needs to reference a fact that lives elsewhere, write the pointer:

```
❌ "The inference engine listens on 8005, the reviewer on 8001..."
✅ "Engine ports and exclusivity: see skill:infra-architecture (single source of truth)"
```

The pointer costs ~15 tokens per turn. The fact costs the same, but goes stale in context and
cannot be corrected retroactively.

## Budget discipline

The always-on file should be *small on purpose*. Every token there is a token not available for
the actual task, and long always-on context measurably degrades instruction-following.

When the budget fills: the answer is not "raise the budget", it's "what here is actually a
procedure or a fact that belongs elsewhere?"

## Reference

- Full rationale: `docs/01-memory-architecture.md`
- Why this maps to CoALA / MemGPT / Anthropic's Skills model: same document, final section
