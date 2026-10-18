# Benchmark: Before / After

> Measured on a real system (1,867 knowledge-base documents, 138 skills, 9 index files)
> on 2026-10-18. Everything here is reproducible with `scripts/benchmark.py`.

---

## The numbers

| Metric | Before | After | Change |
|---|---|---|---|
| **M1 · Dead links in indexes** | **27** | **0** | −27 |
| **M2 · Volatile facts in always-on memory** | **3** | **0** | −3 |
| **M3 · Cross-document fact conflicts** | **3** | **0** | −3 |
| M4 · Memory usage | 96% (2108/2200) | 94% (2070/2200) | −38 chars |

All three error classes went to zero. None were fixed by "being more careful" — each was
fixed by a check that now runs and fails.

---

## How this was measured

```bash
python scripts/benchmark.py \
  --skills ~/.hermes/skills \
  --memory ~/.hermes/memories/MEMORY.md \
  --kb ~/knowledge
```

Output on the current state:

```
M1 索引死链        ✅  0 处  (扫描 9 个索引 / 89 条指向)
M2 易变事实污染    ✅  0 处  (memory 2070/2200 字符, 94%)
M3 跨文档冲突      ✅  0 组  (扫描 244 份文档)

ERROR 级问题总数: 0
```

**Note on M3's scope.** The first version scanned all 1,867 documents and reported "port has
many values" — but it was comparing a 2026-09 log entry against a 2026-10 config. Those aren't
conflicts, they're history. The metric is only meaningful over documents that *claim to
describe the present*: 244 files after excluding dated logs, daily digests, and archives.
**A metric that counts history as contradiction is a metric nobody can act on.**

---

## What each number actually means

### M1 · 27 dead links

Seven index skills pointed at skills that did not exist. Some had been written aspirationally
("there should be a `media-pipeline` skill") and never created; others were renamed.

**Why this is the most dangerous number:** when the agent tries to load a nonexistent skill, it
doesn't crash — it improvises. The output looks fine. The failure is invisible until someone
notices the output doesn't match the process.

Nine of the twenty-seven were in a single index (`index-software`), all pointing at an MMS
toolchain that was described but never built.

### M2 · 3 volatile facts in memory

A port number, a service name, and a model version were living in the always-on memory file.

**Why this is expensive:** memory is re-read from disk each turn, but the *conversation* has
already absorbed the old value. Editing the file does not reach back into running context.
The agent keeps using a stale value with full confidence, and the file looks correct when
inspected.

The 38 characters freed weren't the point — the point is that those facts are now read from a
single ledger at the moment they're needed, so they cannot go stale in context.

### M3 · 3 contradictions across "current-state" documents

The same deployment had three different port assignments across documents, all of which
looked current. Reading any one of them produced a plausible, wrong answer.

Two of the three had been introduced by earlier migrations (a port was changed in the ledger
but not in the design doc; a service was documented at a port it never used).

---

## What we did *not* count, and why

**"The agent forgot something" is not a metric.** It's a symptom with several possible causes,
and counting occurrences doesn't tell you which.

**Skipped routing** — the agent working from instinct instead of loading the routing tree —
is real and was observed repeatedly, but we have not instrumented it. It would require log
analysis of session traces. Listed as *not yet measured* rather than estimated.

**Token cost** is measurable (per-session usage tables) but was not part of this benchmark.

We would rather publish three solid numbers than six estimated ones.

---

## Reproducing on your own system

1. Run the benchmark. Expect M1 > 0 — most systems have dead index links, and they're invisible.
2. Fix them: either create the missing skill or delete the pointer. Never leave a "TODO".
3. Set M2's budget to your own memory limit; adjust `--budget`.
4. For M3, you need a notion of "current-state documents" (`HISTORY_MARKERS` in the script).

The script is intentionally small and dependency-free. It is a starting point, not a product.

---

## Honest caveats

- **One system, one snapshot.** These numbers show that the checks work and that the classes of
  problem are real and prevalent. They do not establish a general improvement rate.
- **Before-numbers were collected manually during the repair** (reading each finding), not by
  running this script against a saved pre-repair snapshot. The *after* numbers are fully
  machine-generated and reproducible.
- **M3 is a heuristic.** It catches "same label, different value" in adjacent text. It will miss
  contradictions phrased differently, and it can be fooled by tables that mention multiple
  values legitimately. Precision was tuned over recall on purpose — see `docs/04-verification.md`.
