# 03 · Pipeline Design: Work Domains, Roles, and Engine Switching

> What we learned running media production, software development, and document work off a
> single shared GPU box — including the part everyone gets wrong: **when to split into
> multiple agents (almost never, and not for the reason you think).**

---

## Part 1 · Competing for one GPU

A single machine with a fixed amount of VRAM/unified memory cannot host every model at once.
There are three strategies:

| Strategy | How | Cost |
|---|---|---|
| **Concurrent** | Keep everything loaded | Impossible past memory limit |
| **Switching** | Load what's needed, unload after | 5–20 min per switch |
| **Hybrid** | One tiny model always on, heavy models swapped | A little of both |

**Switching is the right default**, and the discipline that makes it work is:

> **Batch by task type. Never switch back and forth.**

Concretely: if you're going to generate 40 keyframes, generate all 40 before switching to the
video model — because the switch costs the same whether you use it for one item or forty.
The failure mode of switching isn't the switching itself, it's the *ping-pong*.

Three hard rules that survived:

1. **Exactly one tiny model stays resident.** It handles routing, formatting, small transforms.
   Its job is to make "a quick question" never trigger a 15-minute load.
2. **A memory threshold gates heavy model startup.** If available memory < N, refuse to start
   and say so, rather than OOMing and taking the host down. (On unified-memory machines, an
   OOM is not a process crash — it can hang the whole box.)
3. **Media/GPU engines are mutually exclusive with each other**, not just with LLMs. Image,
   video, and lip-sync all want the same device.

### The scheduling artifact nobody talks about

Once you're switching, **the order of operations becomes a production plan**, not an
implementation detail. Which means the scheduling logic belongs in a script, not in the
agent's judgment — the agent should never be deciding "maybe I'll load the video model now".

Have an explicit interface:

```
engine status          # what's running, what port, how much memory
engine up <name>       # stops conflicting engines, checks the threshold, starts
engine down <name>
```

and a written ledger of `engine → port → memory → exclusivity class` that the agent reads
instead of remembering.

> **Do not let two engines default to the same port.** Two services with no explicit port
> will both take the framework default and become unable to coexist — and the failure appears
> as "it won't start", hours later, with no connection to the real cause. Give every engine an
> explicit port, in a table, and check the table before assigning a new one.

---

## Part 2 · Roles inside a domain

A work domain is a chain of steps, and **the steps have different jobs** — not just different
prompts.

For code:

| Step | Role | What it's responsible for |
|---|---|---|
| 1 | **Designer** | Reads the requirement and the codebase; produces a plan |
| 2 | **Executor** | Writes the code from the plan |
| 3 | **Reviewer** | Finds what's wrong with the code |

**Two kinds of isolation, and they are not interchangeable:**

| Isolation | Cost | Catches | Doesn't catch |
|---|---|---|---|
| **Different position** (separate session, separate instructions) | Free | Blind spots of one viewpoint | Model's inherent weaknesses |
| **Different model** (different weights) | High (a switch) | Weaknesses of one model family | Blind spots of one viewpoint |

The important insight, which is counterintuitive:

> **Reviewing in a fresh session with the same model is real review.
> Reviewing in the same session with a reworded prompt is not.**

Because what makes "self-review" useless is not identical weights — it's that the reviewer has
already seen the answer (anchoring) and remembers why it wrote it (self-justification).
Deliberately reviewing with a *different model* is expensive and should be reserved for the
cases where the model family itself has a known weakness.

So: **layer the review.** Different position every time (free). Different model at the
decision points that matter. And occasionally, an external benchmark to check whether the
yardstick itself is crooked.

**Cross-family review is worth it when it's cheap.** If the reviewer is a small model that can
stay resident alongside the main one, the "expensive" isolation costs nothing — take it.

---

## Part 3 · Splitting into multiple agents

The tempting move is "one agent per domain" — a video agent, a music agent, a coding agent.
This is usually wrong, and here's the test:

> **"If I swapped this agent's model, would it still be the same agent?"**

A video agent with a different model is still the video agent. So the split is real.
But "agent A uses the big model and agent B uses the small model" **is not a split** — it's one
agent with a routing table, and building it as two agents adds coordination cost for nothing.

### What splitting actually buys you

Only isolation:

| Need | Split? |
|---|---|
| Different *judgment* about the same artifact (producer vs. reviewer) | Yes — different positions must be genuinely separate |
| Different permissions (one can touch prod, one can't) | Yes |
| Contexts that must not contaminate each other | Yes |
| Different models | **No** — that's a config setting |
| More parallel throughput | **No** — you have one GPU |

### What splitting costs

- **Handoffs.** Every split creates an interface: how does the downstream agent get the
  artifact? This is where systems die — "A writes, B reviews, but they can't see each other's
  work" is a self-contradicting design.
- **Async is a UX change.** If the specialist is behind a resource switch, the interaction is
  no longer "ask and get an answer" — it's "dispatch and get notified". If you don't say this
  out loud, it feels like the system is broken.
- **Shared state is now a problem.** If two agents read and write the same memory profile,
  each will load the other's writes into its prompt and the result is no longer what you
  configured. Isolate memory, share *code* (skills), not memory.

### The order that actually works

1. **One agent, all domains.** Run the real work until the pipelines are boring.
2. **Write the procedures down as skills.** This is also the future job description of any
   agent you might split off later.
3. **Split only when a specific isolation need appears** — and then it's a copy of a profile
   plus a different instruction set, not a redesign.

Splitting early produces agents whose entire identity is aspirational, because nobody yet knows
what the work actually involves.

---

## Part 4 · Parallel work that doesn't fight

Two things can genuinely run at once without contending for the GPU:

- **Written analysis** (drafting documents, reviewing) — costs API tokens, no local compute
- **Compute work** (downloading, building, rendering) — costs local GPU, no tokens

When someone asks "can these two tasks run together?", the real question is *do they contend
for the same scarce resource*. Two tasks that both want the GPU cannot. A task that wants
tokens and a task that wants nvidia-smi do not contend at all.

Design the split along **resource type**, not along **topic**.
