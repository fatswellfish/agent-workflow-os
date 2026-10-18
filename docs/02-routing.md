# 02 · Routing: One Door In, Pointers Below

> How an agent with 100+ skills finds the right one — and why the failure mode is almost
> never "can't find it" but "didn't look".

---

## The usual design

A single index skill ("routing tree") that classifies the task and points to a category index,
which points to the specific skill:

```
L0  always-on memory        ← one line: "classify the task before acting"
L1  routing tree            ← asks: what kind of work is this?
L2  category indexes        ← 6–10 of them: media / software / docs / infra / review / ops
L3  specific skills         ← 100+
L4  knowledge base          ← facts, decisions, history
```

This is correct. The problem is not the shape.

## The actual failure

In a system using exactly this shape, an audit found that **the agent skipped the routing
tree and started working from its own intuition** — repeatedly. Not because it couldn't find
the skill, but because it never looked.

The routing tree itself had documented the failure mode:

> "The failure isn't 'skill not found'. It's that routing and loading were both skipped, and
> work started from instinct."

Two structural causes make this likely, and neither is a prompt problem:

**1. The top-level trigger competes with the user's actual message.**
A memory line saying "always classify first" is one instruction among many. When the user
asks something concrete and urgent, the concrete request wins.

**2. Indexes have no enforcement.**
Nothing fails when routing is skipped. The agent produces output either way. A skipped
procedure is invisible.

## What actually helps

### Make the entry point impossible to miss, and cheap

The L0 line must be **one line** and must name a concrete action, not a philosophy:

```
❌ "Follow the workflow architecture."
✅ "Any task: load `task-routing-tree` first; it classifies and points."
```

### Make each layer *strictly* cheaper than skipping it

If reading the index takes longer than improvising, improvising wins. An index entry should be
one line: `task → skill-name`. Not a summary of the skill. Not a duplicate of its content.

The index earns its keep only if it's shorter than the alternatives it replaces.

### Make the pointers verifiable

Every name in an index must resolve to a real skill. This is the one thing that *must* be
automated, because a human reviewing an index cannot tell which names exist and which were
written aspirationally:

```bash
python scripts/check.py   # fails if any index entry has no target
```

When a dead pointer is found, there are exactly two correct responses:
**create the target**, or **remove the pointer**. Never leave it as "TODO".

A dead pointer is worse than no pointer, because a *missing* index entry causes the agent to
search (which sometimes works), while a *broken* one causes it to fail a load and then
improvise (which always produces something, and is therefore never noticed).

### Keep category indexes strictly as pointers

A category index should contain:
- one line per skill: what it's for, and its name
- the 2–5 hard rules that apply to that whole category

It should **not** contain the procedure itself. The moment a category index starts carrying
content, it becomes a second source of truth for something a skill already owns, and the two
drift.

---

## Category boundaries that actually worked

Categories should follow **how the work is done**, not how it's labeled. A useful test:
*do these two tasks load the same skills?* If never, they're different categories.
If always, they're one category.

A split that held up under real load:

| Category | Question it answers |
|---|---|
| **Environment / infra** | Where does it run, and is it up? |
| **Software** | How do I change the code? |
| **Media** | How do I produce and verify a media asset? |
| **Render** | What consumes GPU, and in what order? |
| **Documents** | How do I produce a formal artifact? |
| **Review** | How do I check a deliverable? |
| **Knowledge** | Where does this get written down? |
| **Ops** | What runs on a schedule? |

Note that **Render is separate from Media**: producing a storyboard and burning GPU for an
hour are different jobs with different constraints (cost, exclusivity, failure modes). Merging
them produces an index that's correct but useless — the reader still has to guess.

---

## Multi-agent note

Routing is also the decision point for **whether you need more than one agent at all**.

The test that resolves most cases:

> **"If I swapped this agent's model, would it still be the same agent?"**
>
> - Yes → its identity is a *responsibility*. Splitting by it is meaningful.
> - No → it's a model setting. Don't make an agent for it.

We ran one agent across all categories for a long time, deliberately, before splitting any of
it off. See `03-pipeline-design.md` for when splitting actually pays.
