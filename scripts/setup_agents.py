#!/usr/bin/env python3
"""Per-PC setup for other AI tools (run by setup.sh / setup.ps1; safe to re-run).

- OpenAI Codex:      skill link  ~/.agents/skills/code-assist   + hooks in ~/.codex/hooks.json
- Google Antigravity: skill link ~/.gemini/config/skills/code-assist + hooks in ~/.gemini/config/hooks.json
Claude Code needs nothing here (skill lives in ~/.claude/skills; hooks are per project via install).
Hooks are global but do nothing in folders without a .ai/ directory.

  <py> setup_agents.py [--force]   --force: set up tools even if they don't look installed
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CONFIG, IS_WIN, SKILL_DIR, hook_cmd, load_config, read_text, utf8_stdio, write_text  # noqa: E402

HOME = Path(os.path.expanduser("~"))
COPY_MARK = ".code-assist-copy"


def save_python():
    py = os.environ.get("CODE_ASSIST_PY")
    if py:
        c = load_config()
        c["python"] = py
        write_text(CONFIG, json.dumps(c, indent=2))


def _is_link(p):
    return p.is_symlink() or (getattr(p, "is_junction", lambda: False)())


def link_skill(dst):
    src = SKILL_DIR
    if _is_link(dst):
        if os.path.realpath(dst) == os.path.realpath(src):
            return "already linked"
        os.unlink(dst) if dst.is_symlink() else os.rmdir(dst)
    elif dst.exists():
        if not (dst / COPY_MARK).exists():
            return f"skipped: {dst} already exists and isn't ours"
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(src, dst, target_is_directory=True)
        return "linked"
    except (OSError, NotImplementedError):
        pass
    if IS_WIN:  # symlinks need Developer Mode; a junction doesn't
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], capture_output=True)
        if r.returncode == 0:
            return "linked (junction)"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    (dst / COPY_MARK).write_text("copied by setup; re-run setup to refresh\n")
    return "copied (re-run setup after updates)"


def _load(path):
    try:
        return json.loads(read_text(path)) if path.exists() else {}
    except ValueError:
        return None


def _ours(cmd):
    cmd = str(cmd).replace("\\", "/")
    return "scripts/hooks.py" in cmd and ("--agent codex" in cmd or "code-assist" in cmd)


def codex_hooks():
    path = HOME / ".codex" / "hooks.json"
    s = _load(path)
    if s is None:
        return f"skipped: {path} is not valid JSON"
    hooks = s.setdefault("hooks", {})
    wanted = {"SessionStart": (None, "session_start", 15), "UserPromptSubmit": (None, "prompt", 15),
              "PreToolUse": ("Bash", "pre_tool", 15), "PostToolUse": ("Bash|apply_patch", "post_tool", 15),
              "Stop": (None, "stop", 15), "SessionEnd": (None, "session_end", 3)}
    for event, (matcher, arg, timeout) in wanted.items():
        groups = hooks.setdefault(event, [])
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if not _ours(h.get("command", ""))]
        groups[:] = [g for g in groups if g.get("hooks")]
        g = {"hooks": [{"type": "command", "command": hook_cmd(arg, "codex"), "timeout": timeout,
                        "statusMessage": "code-assist"}]}
        groups.append({"matcher": matcher, **g} if matcher else g)
    write_text(path, json.dumps(s, indent=2) + "\n")
    return f"hooks -> {path}  (approve them once in Codex: /hooks)"


def antigravity_hooks():
    path = HOME / ".gemini" / "config" / "hooks.json"
    s = _load(path)
    if s is None:
        return f"skipped: {path} is not valid JSON"

    def h(arg):
        return {"type": "command", "command": hook_cmd(arg, "antigravity"), "timeout": 15}
    s["code-assist"] = {
        "enabled": True,
        "SessionStart": [h("session_start")],
        "PreInvocation": [h("prompt")],
        "PreToolUse": [{"matcher": "view_file|run_command", "hooks": [h("pre_tool")]}],
        "PostToolUse": [{"matcher": "view_file|run_command|write_to_file|replace_file_content|multi_replace_file_content",
                         "hooks": [h("post_tool")]}],
        "Stop": [h("stop")],
    }
    write_text(path, json.dumps(s, indent=2) + "\n")
    return f"hooks -> {path}"


def main():
    utf8_stdio()
    force = "--force" in sys.argv
    save_python()
    print("Other AI tools:")
    if force or (HOME / ".codex").is_dir():
        print("  Codex:       skill " + link_skill(HOME / ".agents" / "skills" / "code-assist"))
        print("               " + codex_hooks())
    else:
        print("  Codex:       not found (~/.codex) - install Codex, then re-run setup")
    if force or (HOME / ".gemini").is_dir():
        print("  Antigravity: skill " + link_skill(HOME / ".gemini" / "config" / "skills" / "code-assist"))
        print("               " + antigravity_hooks())
    else:
        print("  Antigravity: not found (~/.gemini) - install Antigravity, then re-run setup")


if __name__ == "__main__":
    main()
