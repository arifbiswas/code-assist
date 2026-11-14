#!/usr/bin/env python3
"""Token report.   report.py [--days N] [--all]
  default: today, current project.   --all: every project.   --days 7: last 7 days.
"""
import datetime
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SESS_DIR, find_project, read_events  # noqa: E402


def k(n):
    return f"{n / 1_000_000:.2f}M" if n >= 1_000_000 else f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def main():
    days = 1
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    all_proj = "--all" in sys.argv
    proj = None if all_proj else str(find_project() or Path(os.getcwd()).resolve())
    since = (datetime.date.today() - datetime.timedelta(days=days - 1)).isoformat()

    def mine(p):
        return all_proj or p == proj

    use = Counter()
    lifetime = Counter()
    sessions = 0
    for f in SESS_DIR.glob("*.json") if SESS_DIR.exists() else []:
        try:
            s = json.loads(f.read_text())
        except ValueError:
            continue
        if not mine(s.get("project")):
            continue
        hit = False
        for d, b in s.get("by_date", {}).items():
            lifetime.update(b)
            if d >= since:
                use.update(b)
                hit = True
        sessions += hit

    evs = [e for e in read_events() if mine(e.get("project"))]
    recent = [e for e in evs if e.get("date", "") >= since]
    saved_hooks = sum(e["tokens"] for e in recent if e["type"] == "saved")
    saved_life = sum(e["tokens"] for e in evs if e["type"] == "saved")
    partial = sum(1 for e in recent if e["type"] == "saved" and e["detail"].startswith("partial"))
    blocked = sum(1 for e in recent if e["type"] == "saved" and e["detail"].startswith("blocked"))
    edited = {e["detail"] for e in recent if e["type"] == "edit"}
    cache_saved = int(use["cache_read"] * 0.9)  # cache reads cost ~10% of normal input
    total = use["input"] + use["cache_write"] + use["cache_read"] + use["output"]

    label = "today" if days == 1 else f"last {days} days"
    scope = "all projects" if all_proj else Path(proj).name
    print(f"# Token report — {scope}, {label}\n")
    print("## Tokens used")
    print(f"- Sessions: {sessions}   Turns: {use['turns']}")
    print(f"- Input (new): {k(use['input'])}   Cache write: {k(use['cache_write'])}   "
          f"Cache read: {k(use['cache_read'])}   Output: {k(use['output'])}")
    print(f"- Total processed: {k(total)}")
    if total:
        print(f"- Cache hit rate: {use['cache_read'] * 100 // max(total - use['output'], 1)}%")
    print("\n## Tokens saved (estimates)")
    print(f"- Smart reads: {k(saved_hooks)}  ({partial} partial reads, {blocked} blocked junk/vendor reads)")
    print(f"- Prompt cache discount: ~{k(cache_saved)} token-equivalents")
    print(f"- Lifetime smart-read savings: {k(saved_life)}   Lifetime tokens processed: "
          f"{k(sum(lifetime[x] for x in ('input', 'cache_write', 'cache_read', 'output')))}")

    opt = Counter(e["detail"] for e in recent if e["type"] == "optimize")
    print(f"\n## Optimizations ({sum(opt.values())})")
    for d, c in opt.most_common(15):
        print(f"- {d}" + (f"  ×{c}" if c > 1 else ""))
    if not opt:
        print("- (none yet)")

    learned = [e["detail"] for e in recent if e["type"] == "learn"]
    print(f"\n## Learned ({len(learned)})")
    for d in learned[-15:]:
        print(f"- {d}")
    if not learned:
        print("- (nothing new)")

    done = [e["detail"] for e in recent if e["type"] == "done"]
    print(f"\n## Work done ({len(done)} tasks, {len(edited)} files edited)")
    for d in done[-10:]:
        print(f"- {d}")


if __name__ == "__main__":
    main()
