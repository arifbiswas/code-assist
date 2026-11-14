#!/usr/bin/env python3
"""code-assist project installer — same behaviour on macOS, Linux and Windows.

  python3 install.py [project_dir] [--no-agents]
Safe to run again: never overwrites your notes, only refreshes code-assist's own parts.
Usually called through install.sh (macOS/Linux/Git Bash) or install.ps1 (PowerShell).
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symbols  # noqa: E402
from common import (CONFIG, IS_WIN, SKILL_DIR, STORE, USER_PATTERNS, load_config,  # noqa: E402
                    log_event, read_text, script_cmd, utf8_stdio, write_text)

DENY = [
    "Read(./node_modules/**)", "Read(./**/node_modules/**)", "Read(./.next/**)", "Read(./dist/**)",
    "Read(./build/**)", "Read(./coverage/**)", "Read(./.dart_tool/**)", "Read(./ios/Pods/**)",
    "Read(./**/package-lock.json)", "Read(./**/yarn.lock)", "Read(./**/pnpm-lock.yaml)",
    "Read(./**/pubspec.lock)", "Read(./**/composer.lock)", "Read(./**/*.min.js)",
]
HOOKS = {
    "SessionStart": (None, "session_start"),
    "UserPromptSubmit": (None, "prompt"),
    "PreToolUse": ("Read", "pre_tool"),
    "PostToolUse": ("Read|Edit|Write|MultiEdit|NotebookEdit", "post_tool"),
    "Stop": (None, "stop"),
    "SessionEnd": (None, "session_end"),
}
BLOCK_RE = re.compile(r"\n*<!-- (?:code-assist|token-saver):start -->.*?<!-- (?:code-assist|token-saver):end -->\n?", re.S)

PER_PC = [".ai/symbols.txt", ".ai/RULES.md", ".claude/settings.local.json"]

CLAUDE_BLOCK = """<!-- code-assist:start -->
@.ai/RULES.md
@.ai/PATTERNS.md
<!-- code-assist:end -->"""

AGENTS_BLOCK = """<!-- code-assist:start -->
## AI memory (code-assist) — for every AI coding agent
- Before working: read `.ai/PROGRESS.md` (where we left off) and `.ai/LEARNINGS.md`;
  follow `.ai/RULES.md` and `.ai/PATTERNS.md`.
- Locate code: `.ai/CODEMAP.md` -> `grep -n "<name>" .ai/symbols.txt` -> read only that line range.
- After work: overwrite `.ai/PROGRESS.md` (<=12 lines); add new files to `.ai/CODEMAP.md`.
<!-- code-assist:end -->"""


def migrate_old_store():
    """Merge data from the old token-saver name into ~/.claude/code-assist (safe to repeat)."""
    old = Path(os.path.expanduser("~")) / ".claude" / "token-saver"
    if not old.is_dir():
        return
    STORE.mkdir(parents=True, exist_ok=True)
    for item in old.iterdir():
        dest = STORE / item.name
        if item.name == "events.jsonl" and dest.exists():
            with open(dest, "a", encoding="utf-8") as f:
                f.write(read_text(item))
            item.unlink()
        elif item.is_dir() and dest.is_dir():
            for sub in item.iterdir():
                if not (dest / sub.name).exists():
                    shutil.move(str(sub), str(dest / sub.name))
            shutil.rmtree(item, ignore_errors=True)
        elif not dest.exists():
            shutil.move(str(item), str(dest))
    leftover = list(old.iterdir())
    if leftover:
        old.rename(old.with_name("token-saver.migrated"))
    else:
        old.rmdir()
    print("   migrated old token-saver data -> ~/.claude/code-assist")


def save_python(py):
    c = load_config()
    c["python"] = py
    write_text(CONFIG, json.dumps(c, indent=2))


def is_ours(cmd):
    return "scripts/hooks.py" in cmd.replace("\\", "/") and ("code-assist" in cmd or "token-saver" in cmd)


def _load_json(path):
    try:
        return json.loads(read_text(path)) if path.exists() else {}
    except ValueError:
        sys.exit(f"!! {path} is not valid JSON — fix it, then run install again.")


def _strip_ours(hooks):
    for event in list(hooks):
        groups = hooks[event]
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if not is_ours(h.get("command", ""))]
        groups[:] = [g for g in groups if g.get("hooks")]
        if not groups:
            del hooks[event]


def merge_settings(claude_dir, py):
    """Shared, portable rules -> settings.json (commit it).
    Hooks contain this PC's paths -> settings.local.json (per PC, git-ignored)."""
    shared_path, local_path = claude_dir / "settings.json", claude_dir / "settings.local.json"
    shared = _load_json(shared_path)
    deny = shared.setdefault("permissions", {}).setdefault("deny", [])
    deny += [d for d in DENY if d not in deny]
    if "hooks" in shared:  # older versions put hooks here; move them out
        _strip_ours(shared["hooks"])
        if not shared["hooks"]:
            del shared["hooks"]
    write_text(shared_path, json.dumps(shared, indent=2) + "\n")

    s = _load_json(local_path)
    hooks = s.setdefault("hooks", {})
    hook_py = (SKILL_DIR / "scripts" / "hooks.py").as_posix()
    for event, (matcher, arg) in HOOKS.items():
        groups = hooks.setdefault(event, [])
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if not is_ours(h.get("command", ""))]
        groups[:] = [g for g in groups if g.get("hooks")]
        g = {"hooks": [{"type": "command", "command": f'{py} "{hook_py}" {arg}', "timeout": 15}]}
        groups.append({"matcher": matcher, **g} if matcher else g)
    write_text(local_path, json.dumps(s, indent=2) + "\n")


def upsert_block(path, block, header):
    text = read_text(path) if path.exists() else header
    text = BLOCK_RE.sub("\n", text).rstrip() + "\n\n" + block + "\n"
    write_text(path, text)


def main():
    utf8_stdio()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    proj = Path(args[0] if args else os.getcwd()).expanduser().resolve()
    if not proj.is_dir():
        sys.exit(f"!! not a folder: {proj}")
    py = os.environ.get("CODE_ASSIST_PY") or ("python" if IS_WIN else "python3")

    migrate_old_store()
    save_python(py)
    ai = proj / ".ai"
    ai.mkdir(exist_ok=True)

    # 1) memory files: created only if missing; RULES.md is skill-owned and refreshed
    for name in ("CODEMAP", "PATTERNS", "PROGRESS", "LEARNINGS", "HISTORY"):
        if not (ai / f"{name}.md").exists():
            shutil.copy(SKILL_DIR / "templates" / f"{name}.md", ai / f"{name}.md")
    rules = read_text(SKILL_DIR / "templates" / "RULES.md").replace("{{LOG}}", script_cmd("log.py"))
    write_text(ai / "RULES.md", rules)
    if not USER_PATTERNS.exists():
        write_text(USER_PATTERNS, "# User preferences (all projects)\n")

    # 2) Claude Code: CLAUDE.md imports + hooks; other agents: AGENTS.md
    upsert_block(proj / "CLAUDE.md", CLAUDE_BLOCK, f"# {proj.name}\n")
    if "--no-agents" not in sys.argv:
        upsert_block(proj / "AGENTS.md", AGENTS_BLOCK, f"# {proj.name}\n")
    merge_settings(proj / ".claude", py)

    # 3) per-PC / generated files stay out of git (regenerated by install on every PC)
    gi = proj / ".gitignore"
    if gi.exists() or (proj / ".git").exists():
        cur = read_text(gi)
        missing = [x for x in PER_PC if x not in cur.splitlines()]
        if missing:
            write_text(gi, cur.rstrip("\n") + ("\n" if cur.strip() else "")
                       + "# code-assist (per PC, regenerated by install)\n" + "\n".join(missing) + "\n")

    files, syms = symbols.rebuild(proj)
    log_event(proj, "optimize", "code-assist installed")

    print(f"✅ code-assist installed in {proj}")
    print(f"   indexed {files} files, {syms} symbols -> .ai/symbols.txt")
    if files > 5:
        print("   EXISTING project -> ask your AI:  /code-assist init  (Codex: $code-assist init)  to build CODEMAP + PATTERNS once")
    else:
        print("   NEW project -> memory files fill up automatically as you work.")
    print("   Start a NEW chat/session in this folder so the hooks load.")
    print("   Commit .ai/*.md, CLAUDE.md, AGENTS.md, .claude/settings.json. On another PC, run install there too.")


if __name__ == "__main__":
    main()
