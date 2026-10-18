---
name: consistency-check
description: "Use when 改完知识库或skill后自检一致性: 死链/易变事实污染/跨文档冲突，机器可复现。"
---

# Consistency Check

> A skill wrapping `scripts/benchmark.py` — run it before declaring any documentation or
> skill change "done".

## When to Use

- Before reporting a documentation/skill change as complete
- After adding a new index entry or skill
- After changing any deployment fact (port, path, model, version)
- Weekly, as a standing audit

## The rule

> **"Done" means the checker passes — not "I updated the doc".**

If the checker fails, the work isn't finished. There is no "I'll fix the links later".
A broken pointer is worse than a missing one: the agent fails a load and improvises,
producing confident wrong output with no error.

## Procedure

```bash
# 1. Run the benchmark
python scripts/benchmark.py --skills <skills-dir> --memory <memory-file> --kb <kb-dir>

# 2. If M1 (dead links) > 0:
#    For each dead link, choose exactly one:
#      a) create the target skill  → then it's a real pointer
#      b) delete the pointer       → then it's an honest absence
#    Never leave it as a TODO or a "coming soon".

# 3. If M2 (memory pollution) > 0:
#    Move the volatile fact to the single source of truth (a skill or a ledger doc),
#    and replace it in memory with a pointer:
#      ❌ "engine A listens on 8005"
#      ✅ "engine ports: see skill:infra-architecture"

# 4. If M3 (conflicts) > 0:
#    Determine which value is currently true (check the running system, not the docs).
#    Update the loser to match, or mark it as historical and move it to the archive.

# 5. Re-run until ERROR count is 0.
```

## Common traps

| Trap | What happens | Fix |
|---|---|---|
| "I'll fix the links later" | The pointer keeps silently shaping behavior | Fix now, or delete the pointer now |
| Fixing doc B to match doc A when A is wrong | Propagates the error to a second place | Always verify against the *running system*, never against another document |
| Adding a check that cries wolf | Checker gets ignored, then disabled | Tune for precision; exempt historical/hand-written lines |
| Leaving history in scope for conflict checks | Old logs "conflict" with current state; the report is noise | Exclude dated files and archive directories |
| Treating WARN as ERROR | Real errors get lost in the noise | WARN = backlog, ERROR = blocks completion |

## What this does not check

- Whether the *content* is correct (that needs a reviewer, not a script)
- Whether the agent actually followed the routing tree (needs log instrumentation)
- Token cost (needs usage-table access)

Listing what a check doesn't cover is what keeps it trustworthy.

## Reference

- Full rationale: `docs/04-verification.md`
- Metrics definition: `docs/05-benchmark.md`
- Script: `scripts/benchmark.py`
