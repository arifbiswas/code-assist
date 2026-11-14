#!/usr/bin/env python3
"""Merge token-saver hooks + deny rules into <project>/.claude/settings.json (idempotent, keeps existing)."""
import json
import sys
from pathlib import Path

DENY = [
    "Read(./node_modules/**)", "Read(./**/node_modules/**)", "Read(./.next/**)", "Read(./dist/**)",
    "Read(./build/**)", "Read(./coverage/**)", "Read(./.dart_tool/**)", "Read(./ios/Pods/**)",
    "Read(./**/package-lock.json)", "Read(./**/yarn.lock)", "Read(./**/pnpm-lock.yaml)",
    "Read(./**/pubspec.lock)", "Read(./**/composer.lock)", "Read(./**/*.min.js)",
]


def main():
    settings_path, skill_dir = Path(sys.argv[1]), sys.argv[2]
    cmd = lambda ev: f'python3 "{skill_dir}/scripts/hooks.py" {ev}'  # noqa: E731
    wanted = {
        "SessionStart": (None, "session_start"),
        "UserPromptSubmit": (None, "prompt"),
        "PreToolUse": ("Read", "pre_tool"),
        "PostToolUse": ("Read|Edit|Write|MultiEdit|NotebookEdit", "post_tool"),
        "Stop": (None, "stop"),
        "SessionEnd": (None, "session_end"),
    }
    try:
        s = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    except ValueError:
        print(f"!! {settings_path} is not valid JSON — fix it, then re-run install.")
        sys.exit(1)
    deny = s.setdefault("permissions", {}).setdefault("deny", [])
    for d in DENY:
        if d not in deny:
            deny.append(d)
    hooks = s.setdefault("hooks", {})
    for event, (matcher, arg) in wanted.items():
        groups = hooks.setdefault(event, [])
        # drop older token-saver entries (path may have changed), then add fresh
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if "token-saver" not in h.get("command", "")
                          or "scripts/hooks.py" not in h.get("command", "")]
        groups[:] = [g for g in groups if g.get("hooks")]
        g = {"hooks": [{"type": "command", "command": cmd(arg), "timeout": 15}]}
        if matcher:
            g = {"matcher": matcher, **g}
        groups.append(g)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(s, indent=2) + "\n")


if __name__ == "__main__":
    main()
