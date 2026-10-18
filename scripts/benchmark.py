#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark.py — 测量一个 agent 指令系统的健康度

用法:
    python benchmark.py --skills ~/.hermes/skills --kb ~/knowledge --memory ~/.hermes/memories/MEMORY.md
    python benchmark.py --json          # 机器可读输出

输出四类指标，每类可独立复现:

  M1  索引死链数        index skill 指向了不存在的 skill
  M2  易变事实污染       always-on memory 里出现端口/路径/模型名
  M3  跨文档事实冲突     同一事实在多份"现状文档"里取值不一致
  M4  memory 占用率     占预算百分比
"""
import os, re, sys, glob, json, argparse, io

# ---------------- 配置默认值（可被参数覆盖） ----------------

DEFAULT_SKILLS = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.local/share")),
                              "hermes", "skills")
DEFAULT_MEMORY = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.local/share")),
                              "hermes", "memories", "MEMORY.md")

# 内置工具名（不是 skill，不应被判为死链）
BUILTIN = {
    "search_files", "read_file", "write_file", "patch", "terminal", "execute_code",
    "delegate_task", "todo_list", "session_search", "browser_exec", "web_search",
    "web_extract", "vision_analyze", "cronjob_manage", "text_to_speech", "clarify",
    "skill_view", "skill_manage", "skills_list", "memory",
}

# 易变事实的正则库
VOLATILE = [
    (re.compile(r"\b(?:port\s*)?(?:80\d\d|81\d\d|98\d\d)\b"), "端口号"),
    (re.compile(r"[A-Za-z]:\\\\[A-Za-z]"), "Windows 绝对路径"),
    (re.compile(r"/(?:home|opt|usr/local)/[a-z]"), "Unix 绝对路径"),
    (re.compile(r"\.safetensors\b|\.gguf\b|\.ckpt\b"), "模型文件名"),
    (re.compile(r"\b(?:vllm|ollama|llama-swap)-[a-z0-9-]+\b"), "服务/unit 名"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "IP 地址"),
]

# 冲突检测：同一行内 "关键词 ... 值" 的紧邻绑定
CONFLICT_PAIRS = [
    # (事实类别, 关键词候选, 值的正则)
    ("port", ["port", "端口"], re.compile(r"(?:port\s*[:=]?\s*|:)(\d{4,5})\b")),
]


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return None


# ---------------- M1: 索引死链 ----------------

def measure_dead_links(skills_dir):
    """返回 (死链列表, 索引文件数, 总指向数)"""
    names = set()
    index_files = []
    for p in glob.glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True):
        t = read(p)
        if not t:
            continue
        m = re.search(r"^name:\s*(.+)$", t, re.M)
        if m:
            names.add(m.group(1).strip().strip("\"'"))
        base = os.path.basename(os.path.dirname(p))
        if base.startswith("index-") or base in ("task-routing-tree",):
            index_files.append((base, p))

    dead = []
    total_refs = 0
    NEG = ("已废弃", "不存在", "从未", "历史遗留", "deprecated", "no longer")
    for base, p in index_files:
        t = read(p) or ""
        for ln, line in enumerate(t.splitlines(), 1):
            if any(k in line for k in NEG):
                continue
            for c in set(re.findall(r"`([a-z][a-z0-9_-]{2,40})`", line)):
                if c in BUILTIN or "." in c or "/" in c:
                    continue
                total_refs += 1
                if c not in names:
                    dead.append({"index": base, "target": c, "line": ln})
    return dead, len(index_files), total_refs


# ---------------- M2: memory 污染 ----------------

def measure_memory_pollution(memory_path, budget=2200):
    t = read(memory_path)
    if t is None:
        return None
    hits = []
    for pat, label in VOLATILE:
        for m in pat.finditer(t):
            s = max(0, m.start() - 20)
            hits.append({
                "type": label,
                "value": m.group(0),
                "context": t[s:m.end() + 10].replace("\n", " "),
            })
    return {
        "chars": len(t),
        "budget": budget,
        "usage_pct": round(len(t) / budget * 100, 1),
        "violations": hits,
    }


# ---------------- M3: 跨文档事实冲突 ----------------

def measure_conflicts(docs):
    """
    只在"声称描述现状"的文档间比对同一事实的取值。

    关键：历史日志/日报/归档里出现的端口是"当时的值"，不是冲突。
    必须先圈定 scope，否则每天的历史记录都会互相"冲突"，结论无意义。
    """
    # 历史/归档类目录——其中的值记录的是"当时"，不做现状比对
    HISTORY_MARKERS = (
        "daily-chat", "social-intel", "intel", "_archive", "_generated", "_raw",
        "log.md", "index.md", "evidence_pack",
    )
    current_docs = []
    for p in docs:
        rel = p.replace("\\", "/").lower()
        if any(m in rel for m in HISTORY_MARKERS):
            continue
        # 文件名带日期的，视为时间点记录
        if re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(p)):
            continue
        current_docs.append(p)

    bindings = {}
    for p in current_docs:
        t = read(p)
        if not t:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            for cat, kws, valre in CONFLICT_PAIRS:
                for kw in kws:
                    for m in re.finditer(re.escape(kw) + r"[^\n]{0,30}?" + valre.pattern, line, re.I):
                        v = m.group(1)
                        bindings.setdefault(kw, {}).setdefault(v, []).append(
                            "%s:%d" % (os.path.basename(p), ln))
    conflicts = []
    for kw, vals in bindings.items():
        if len(vals) > 1:
            conflicts.append({"label": kw, "values": {k: v[:3] for k, v in vals.items()}})
    return conflicts, len(current_docs)


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", default=DEFAULT_SKILLS)
    ap.add_argument("--memory", default=DEFAULT_MEMORY)
    ap.add_argument("--kb", default="")
    ap.add_argument("--budget", type=int, default=2200)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = {"paths": {"skills": args.skills, "memory": args.memory, "kb": args.kb}}

    # M1
    if os.path.isdir(args.skills):
        dead, n_idx, n_refs = measure_dead_links(args.skills)
        report["M1_dead_links"] = {
            "count": len(dead),
            "index_files": n_idx,
            "total_refs": n_refs,
            "items": dead[:20],
        }
    else:
        report["M1_dead_links"] = {"error": "skills dir not found"}

    # M2
    mem = measure_memory_pollution(args.memory, args.budget)
    report["M2_memory"] = mem if mem else {"error": "memory file not found"}

    # M3
    if args.kb and os.path.isdir(args.kb):
        docs = glob.glob(os.path.join(args.kb, "**", "*.md"), recursive=True)
        docs = [d for d in docs if os.path.getsize(d) < 200_000]
        conf, n = measure_conflicts(docs)
        report["M3_conflicts"] = {"count": len(conf), "docs_scanned": n, "items": conf[:10]}
    else:
        report["M3_conflicts"] = {"skipped": "no --kb given"}

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    # 人类可读
    print("=" * 60)
    print("Agent 指令系统健康度基准")
    print("=" * 60)

    m1 = report["M1_dead_links"]
    if "error" in m1:
        print("\nM1 索引死链: 无法测量 (%s)" % m1["error"])
    else:
        status = "✅" if m1["count"] == 0 else "❌"
        print("\nM1 索引死链        %s  %d 处  (扫描 %d 个索引 / %d 条指向)"
              % (status, m1["count"], m1["index_files"], m1["total_refs"]))
        for it in m1["items"][:10]:
            print("     - %s → `%s` (行 %d)" % (it["index"], it["target"], it["line"]))

    m2 = report["M2_memory"]
    if "error" in m2:
        print("\nM2 memory 检查: 无法测量 (%s)" % m2["error"])
    else:
        status = "✅" if not m2["violations"] else "❌"
        print("\nM2 易变事实污染    %s  %d 处  (memory %d/%d 字符, %.0f%%)"
              % (status, len(m2["violations"]), m2["chars"], m2["budget"], m2["usage_pct"]))
        for v in m2["violations"][:8]:
            print("     - [%s] %s   ...%s..." % (v["type"], v["value"], v["context"][:60]))

    m3 = report["M3_conflicts"]
    if "skipped" in m3:
        print("\nM3 跨文档冲突: 跳过 (需 --kb)")
    else:
        status = "✅" if m3["count"] == 0 else "⚠️"
        print("\nM3 跨文档冲突      %s  %d 组  (扫描 %d 份文档)"
              % (status, m3["count"], m3["docs_scanned"]))
        for c in m3["items"]:
            print("     - %s 有多个取值: %s" % (c["label"], c["values"]))

    print("\n" + "=" * 60)
    total_errors = (m1.get("count", 0) if "error" not in m1 else 0) + \
                   (len(m2.get("violations", [])) if "error" not in m2 else 0)
    print("ERROR 级问题总数: %d" % total_errors)
    print("=" * 60)
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
