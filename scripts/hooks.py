#!/usr/bin/env python3
"""code-assist hook dispatcher.  Usage (from .claude/settings.json):
    python3 <skill>/scripts/hooks.py <session_start|prompt|pre_tool|post_tool|stop|session_end>

Never breaks the session: any error -> silent exit 0.
Only active in projects that have a .ai/ folder (created by install.sh).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symbols  # noqa: E402
from common import (BINARY_EXT, CODE_EXT, IS_WIN, SKILL_DIR, STORE, USER_PATTERNS,  # noqa: E402
                    cfg, drop_state, est_tokens, is_generated, load_state, log_event,
                    project_dir, read_text, record_usage, rel, save_state, script_cmd,
                    session_usage, strip_comments, utf8_stdio)

LOG = script_cmd("log.py")

CORRECTION_RE = re.compile(
    r"\b(vul|bhul|wrong|don'?t|dont|never|always|instead|revert|undo|prefer|"
    r"eivabe na|evabe na|amon na|emon na|thik na|hoy ?ni|sob ?somoy|kokhono|"
    r"pochondo|kora jabe na|korba na|korbe na|change kor[ob]? na|ager moto)\b"
    r"|ভুল|সবসময়|কখনো|পছন্দ|এভাবে না|করবে না|করবা না", re.I)


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)


def context(event, text):
    emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def head(path, n):
    text = strip_comments(read_text(path)).strip()
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("# ")]
    if len(lines) > n:
        lines = lines[:n] + [f"...(+{len(lines) - n} lines in {Path(path).name})"]
    return "\n".join(lines)


def tail(path, n):
    lines = [ln for ln in strip_comments(read_text(path)).splitlines() if ln.strip().startswith("-")]
    return "\n".join(lines[-n:])


# ---------------------------------------------------------------- SessionStart
def session_start(data, proj):
    if data.get("source") == "resume":
        return
    ai = proj / ".ai"
    if not (ai / "symbols.txt").exists():
        kw = ({"creationflags": 0x00000008 | 0x00000200} if IS_WIN  # DETACHED | NEW_PROCESS_GROUP
              else {"start_new_session": True})
        subprocess.Popen([sys.executable, str(SKILL_DIR / "scripts" / "symbols.py"), str(proj)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, **kw)
    parts = ["[code-assist] Project memory (auto-loaded; do not re-read these files):"]
    for title, path, fn, n in [
        ("PROGRESS (where we left off)", ai / "PROGRESS.md", head, 15),
        ("Recent history", ai / "HISTORY.md", tail, 5),
        ("Project learnings", ai / "LEARNINGS.md", head, 30),
        ("User's global preferences", USER_PATTERNS, head, 30),
    ]:
        body = fn(path, n)
        if body and "(empty)" not in body:
            parts.append(f"## {title}\n{body}")
    parts.append("Locate code: .ai/CODEMAP.md -> grep -n '<name>' .ai/symbols.txt -> Read with offset/limit.")
    save_state(data.get("session_id"), {"edits_since_progress": 0, "pending_map": [], "clear_warned_at": 0})
    context("SessionStart", "\n\n".join(parts))


# ------------------------------------------------------------ UserPromptSubmit
def prompt(data, proj):
    sid = data.get("session_id")
    st = load_state(sid)
    notes = []
    ctx = session_usage(data.get("transcript_path"))["context"]
    limit = cfg("CLEAR_AT", 80000)
    if ctx >= limit and ctx >= st.get("clear_warned_at", 0) + 30000:
        st["clear_warned_at"] = ctx
        notes.append(
            f"[code-assist] Context is ~{ctx // 1000}k tokens (expensive: every message re-sends it). "
            "When this task is done: overwrite .ai/PROGRESS.md (<=12 lines) and run "
            f"{LOG} done \"<one line>\", then end your reply with: "
            "\"✅ Progress saved — type /clear to continue cheaply (memory reloads automatically).\"")
        log_event(proj, "optimize", f"context hit {ctx // 1000}k -> saved progress & suggested /clear")
    if CORRECTION_RE.search(data.get("prompt", "")):
        notes.append(
            "[code-assist] If this message corrects you or states a preference/habit, record it once: "
            f"{LOG} learn \"<lesson>\" (add --global if it applies to all projects). Skip if already recorded.")
    save_state(sid, st)
    if notes:
        context("UserPromptSubmit", "\n".join(notes))


# ----------------------------------------------------------------- PreToolUse
def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "deny",
                                 "permissionDecisionReason": reason}})


def pre_tool(data, proj):
    if data.get("tool_name") != "Read":
        return
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path")
    r = rel(proj, fp) if fp else None
    if not r:
        return
    p = Path(fp)
    if p.suffix.lower() in BINARY_EXT or not p.is_file():
        return
    if is_generated(r):
        size = p.stat().st_size
        log_event(proj, "saved", f"blocked read of generated/vendor file {r}", est_tokens(size))
        deny(f"[code-assist] {r} is generated/vendor code (~{est_tokens(size)} tokens). "
             "Grep it for the exact thing you need instead. If the user explicitly needs it, use "
             "`sed -n 'A,Bp'` on a small range.")
    if ti.get("offset") or ti.get("limit"):
        return
    text = read_text(p)
    n = text.count("\n") + 1
    if n <= cfg("BIG_FILE_LINES", 300):
        return
    deny(f"[code-assist] {r} has {n} lines (~{est_tokens(len(text))} tokens). Don't read it whole. "
         f"Symbols (line: kind name):\n{symbols.outline(proj, p)}\n"
         "Read only the range you need (offset/limit, ~±40 lines) or grep -n first. "
         f"If you truly need the entire file, call Read again with limit={n}.")


# ---------------------------------------------------------------- PostToolUse
def post_tool(data, proj):
    tool = data.get("tool_name")
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("notebook_path")
    r = rel(proj, fp) if fp else None
    if not r:
        return
    p = Path(fp)
    sid = data.get("session_id")
    st = load_state(sid)
    if tool == "Read":
        if ti.get("offset") or ti.get("limit"):
            lines = read_text(p).splitlines(keepends=True)
            start = max(int(ti.get("offset") or 1) - 1, 0)
            part = lines[start:start + int(ti.get("limit") or 2000)]
            saved = est_tokens(sum(map(len, lines)) - sum(map(len, part)))
            if saved >= 100:
                log_event(proj, "saved", f"partial read {r} ({len(part)}/{len(lines)} lines)", saved)
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        if r.startswith(".ai/"):
            if p.name == "PROGRESS.md":
                st["edits_since_progress"] = 0
            if p.name == "CODEMAP.md":
                cm = read_text(p)
                st["pending_map"] = [f for f in st.get("pending_map", []) if f not in cm]
        elif not r.startswith(".claude"):
            st["edits_since_progress"] = st.get("edits_since_progress", 0) + 1
            symbols.update_file(proj, p)
            if tool == "Write" and p.suffix.lower() in CODE_EXT and "test" not in p.name.lower():
                cm = read_text(proj / ".ai" / "CODEMAP.md")
                if r not in cm and r not in st.get("pending_map", []):
                    st.setdefault("pending_map", []).append(r)
            log_event(proj, "edit", r)
    save_state(sid, st)


# ----------------------------------------------------------------------- Stop
def stop(data, proj):
    record_usage(data, proj)
    if data.get("stop_hook_active"):
        return
    sid = data.get("session_id")
    st = load_state(sid)
    cm = read_text(proj / ".ai" / "CODEMAP.md")
    pend = [f for f in st.get("pending_map", []) if f not in cm and (proj / f).exists()]
    st["pending_map"] = pend
    todo, what = [], []
    if pend:
        todo.append("add to .ai/CODEMAP.md (1 line each: feature -> file -> main symbols): " + ", ".join(pend[:10]))
        what.append(f"CODEMAP +{len(pend)} files")
        st["pending_map"] = []  # ask once per batch
    if st.get("edits_since_progress", 0) >= cfg("PROGRESS_EVERY", 4):
        todo.append(f"overwrite .ai/PROGRESS.md (<=12 lines: done / in progress / next / open issues) and run {LOG} done \"<one line summary>\"")
        what.append("PROGRESS/HISTORY")
        st["edits_since_progress"] = 0
    save_state(sid, st)
    if todo:
        log_event(proj, "optimize", "auto memory update: " + ", ".join(what))
        emit({"decision": "block",
              "reason": "[code-assist] Before finishing, quietly do this (no explanation to the user): "
                        + "; ".join(todo) + ". Then stop."})


# ----------------------------------------------------------------- SessionEnd
def session_end(data, proj):
    record_usage(data, proj)
    drop_state(data.get("session_id"))


HANDLERS = {"session_start": session_start, "prompt": prompt, "pre_tool": pre_tool,
            "post_tool": post_tool, "stop": stop, "session_end": session_end}


def main():
    utf8_stdio()
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    proj = project_dir(data)
    if event not in HANDLERS or not (proj / ".ai").is_dir():
        sys.exit(0)
    try:
        HANDLERS[event](data, proj)
    except SystemExit:
        raise
    except Exception as e:  # never break the user's session
        try:
            STORE.mkdir(parents=True, exist_ok=True)
            with open(STORE / "errors.log", "a", encoding="utf-8") as f:
                f.write(f"{event}: {e!r}\n")
        except OSError:
            pass
    sys.exit(0)


if __name__ == "__main__":
    main()
