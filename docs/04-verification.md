# 04 · Verification: Consistency That Runs Itself

> The core claim of this repo: **consistency is not a habit, it's a check.**
> If it depends on someone remembering, it will fail — including when that someone is an agent.

---

## Why "I'll keep them in sync" never works

Three independent forces guarantee drift:

1. **Write paths multiply.** A fact can be written by a human, by the agent, by a scheduled
   job, and by a copy-paste — each of which believes it's authoritative.
2. **Read paths are asynchronous.** A fact updated in file A doesn't retract a copy already in
   file B, or in a running conversation.
3. **Nobody notices.** A contradiction produces no error. Both values are "valid" text. The
   only way to discover it is to compare, and nobody compares until something breaks.

So: **the check must be a program, and it must run at the only moment it can prevent damage —
right before the write is considered done.**

---

## The ownership table

The prerequisite for detecting a contradiction is defining what a contradiction *is*. That
requires declaring, for each class of fact, the one file allowed to define it.

Example (this is the actual shape we use):

| Fact class | Single home | Everyone else |
|---|---|---|
| Service ports / hardware | `skills/infra-architecture` | writes "see infra-architecture", never a number |
| Pipeline steps / roles | `docs/pipeline-table.md` | references only |
| Credentials | environment file | **never written in any document** |
| Behavioral rules | always-on memory | — |
| Procedures | the relevant skill | — |

Once this table exists, a contradiction is mechanically detectable: *the same fact class
appearing with different values in two places*.

Without it, "conflict" is a matter of taste, and the agent will resolve it by whichever value
it happens to read first.

---

## The checks that paid for themselves

### 1. Referential integrity of indexes

**What it catches:** an index entry pointing at a skill that doesn't exist.

**Why it matters most:** the failure is silent. The agent can't load the target, so it
improvises, and the output looks fine. A broken link is *worse* than a missing link.

**Implementation:** parse every index skill, extract candidate skill names, resolve against the
actual skill directory. Fail on misses.

In one audit: **27 dead links across 7 index skills** — and they had been silently shaping
behavior for weeks.

### 2. Volatile-fact leakage into memory

**What it catches:** port numbers, absolute paths, model filenames, service names appearing in
the always-on memory file.

**Implementation:** regex bank against the memory file. Any hit is an error, not a warning —
because this failure is expensive and permanent (see `01-memory-architecture.md`).

### 3. Cross-document value consistency

**What it catches:** a ledger says port 8005, a design doc says 8001, both look current.

**The hard part is precision.** A naive "find numbers near keywords" matcher produced 10
findings in our corpus, of which 9 were historical narrative ("we moved from 8190 to 8191
last month") and 1 was real. A checker that cries wolf gets disabled, and then it's worth
nothing.

**What made it usable:** require the keyword and the value to be *adjacent* (within N
characters), and exempt lines marked as historical/corrective. With that, 10 findings became
1 real one, then 0 after the fix.

> **Design rule: a check that produces false positives is worse than no check**, because the
> human cost of triaging it exceeds the value. Tune for precision, not recall.

### 4. Structural completeness

**What it catches:** documents missing their metadata block (title/date/type), which silently
breaks search and staleness detection.

**Treat as warnings, not errors** — this is backlog, not breakage. Mixing "the system is
inconsistent" with "the system is untidy" makes the error signal useless.

---

## Severity model

| Level | Meaning | Response |
|---|---|---|
| **ERROR** | Something is actively wrong now; behavior will be incorrect | Block. Do not declare done. |
| **WARN** | Backlog. Real but not currently misleading anyone. | Report, schedule |

Only ERROR exits non-zero. The exit code is the contract: **a tool that reports problems but
exits 0 is a tool nobody obeys.**

---

## Wiring it into the loop

The check is only real if it runs. Three places:

1. **After any write to a skill or a fact-bearing document.** Cheapest, catches it at the
   moment of creation.
2. **At the end of a work session**, before reporting completion.
3. **On a schedule** (nightly/weekly) — catches drift introduced by edits that bypassed step 1.

And one rule for the agent itself:

> **"Done" means the checker passes.** Not "I updated the doc." Not "I think it's consistent."
> The check runs, and its output is the evidence.

This is the same principle as a test suite: you don't trust the developer's claim that tests
pass, you run them.

---

## Minimal viable version

If you're starting from nothing, do these two things in this order:

**1. Referential integrity checker** (~40 lines)
```
for each index file: extract `names`, assert each exists in the skill dir
```
This single check eliminates the highest-frequency silent failure.

**2. Ownership table**
```
one markdown table declaring: fact class → single home
```
This makes every subsequent check well-defined.

Everything else — cross-document diffing, frontmatter linting, scheduled audits — is
incremental. Start with the two.

---

## What we deliberately did *not* build

- **A vector database over the knowledge base.** The problem was contradiction, not recall.
  Adding embeddings would have made retrieval smoother while leaving the contradictions intact.
- **A fifth layer of indexing.** More indirection between the reader and the content. The
  existing layers were sufficient; they were just unverified.
- **Automatic rewriting of conflicting documents.** A checker that edits is a checker nobody
  can trust. It reports; a human or an agent decides.
- **A general-purpose "consistency AI".** Every check we kept is deterministic and free. The
  ones that needed judgment were too unreliable to gate on.
