#!/usr/bin/env python3
"""One-command memory writes (cheaper than editing files by hand).

  log.py learn "<lesson>" [--global]   -> .ai/LEARNINGS.md (or ~/.claude/code-assist/USER_PATTERNS.md)
  log.py pattern "<convention>"        -> .ai/PATTERNS.md
  log.py done "<what was finished>"    -> .ai/HISTORY.md (dated changelog, never loaded whole)
  log.py optimize "<what>" [tokens]    -> optimization log (shown in report)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import USER_PATTERNS, find_project, log_event, read_text, today, utf8_stdio, write_text  # noqa: E402


def append_line(path, line, header):
    text = read_text(path) if path.exists() else f"# {header}\n\n"
    body = line.split("] ", 1)[-1].strip().lower()
    if any(body == ln.split("] ", 1)[-1].strip().lower() for ln in text.splitlines()):
        return False  # duplicate
    if not text.endswith("\n"):
        text += "\n"
    write_text(path, text + line + "\n")
    return True


def main():
    utf8_stdio()
    args = [a for a in sys.argv[1:] if a != "--global"]
    is_global = "--global" in sys.argv
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    kind, text = args[0], args[1].strip()
    proj = find_project() or Path(os.getcwd())
    ai = proj / ".ai"
    if kind == "learn":
        target = USER_PATTERNS if is_global else ai / "LEARNINGS.md"
        header = "User preferences (all projects)" if is_global else "Project learnings"
        added = append_line(target, f"- [{today()}] {text}", header)
        if added:
            log_event(proj, "learn", text + (" (global)" if is_global else ""))
        print("learned" if added else "already known")
    elif kind == "pattern":
        added = append_line(ai / "PATTERNS.md", f"- {text}", "Code patterns")
        if added:
            log_event(proj, "learn", "pattern: " + text)
        print("pattern saved" if added else "already known")
    elif kind == "done":
        append_line(ai / "HISTORY.md", f"- [{today()}] {text}", "History")
        log_event(proj, "done", text)
        print("history updated")
    elif kind == "optimize":
        tokens = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
        log_event(proj, "optimize", text, tokens)
        print("logged")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
