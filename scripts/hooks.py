#!/usr/bin/env python3
"""code-assist hook dispatcher for Claude Code, OpenAI Codex, Google Antigravity and Cursor.

    <py> hooks.py <session_start|prompt|pre_tool|post_tool|stop|session_end> [--agent claude|codex|antigravity|cursor]

Each tool's JSON is normalised to one internal shape, handled once, and answered in that
tool's own output format. Never breaks a session: any error -> silent, permissive exit.
Only active in projects that have a .ai/ folder (created by install).
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
AGENT = "claude"
EMITTED = False

CORRECTION_RE = re.compile(
    r"\b(vul|bhul|wrong|don'?t|dont|never|always|instead|revert|undo|prefer|"
    r"eivabe na|evabe na|amon na|emon na|thik na|hoy ?ni|sob ?somoy|kokhono|"
    r"pochondo|kora jabe na|korba na|korbe na|change kor[ob]? na|ager moto)\b"
    r"|ভুল|সবসময়|কখনো|পছন্দ|এভাবে না|করবে না|করবা না", re.I)

# shell reads (Codex / Antigravity run files through the shell)
_P = r"""(["']?)([^\s"'|;&<>]+)"""
WHOLE_READ = re.compile(r"^(?:cat|bat|less|more|type|Get-Content|gc|nl)(?:\s+-\w+)*\s+" + _P + r"\1\s*$")
SED_READ = re.compile(r"""^sed\s+-n\s+["']?(\d+)\s*,\s*(\d+)\s*p["']?\s+""" + _P + r"\3\s*$")
HEAD_READ = re.compile(r"^head\s+-n\s*(\d+)\s+" + _P + r"\2\s*$")
PATCH_FILE = re.compile(r"^\*\*\* (Add|Update|Delete) File:\s*(.+?)\s*$", re.M)
PATCH_MOVE = re.compile(r"^\*\*\* Move to:\s*(.+?)\s*$", re.M)

AG_TOOLS = {"view_file": "Read", "write_to_file": "Write", "replace_file_content": "Edit",
            "multi_replace_file_content": "Edit", "run_command": "Bash"}


# ------------------------------------------------------------------ output
def emit(obj):
    global EMITTED
    EMITTED = True
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)


def add_context(event, text):
    if AGENT == "antigravity":
        emit({"injectSteps": [{"systemMessage": text}]})
    if AGENT == "cursor":
        emit({"additional_context": text})
    emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def deny(reason):
    if AGENT == "antigravity":
        emit({"decision": "deny", "reason": reason})
    if AGENT == "cursor":
        emit({"permission": "deny", "agent_message": reason,
              "user_message": "code-assist: blocked a wasteful file read"})
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "deny",
                                 "permissionDecisionReason": reason}})


def block_stop(reason):
    if AGENT == "cursor":
        emit({"followup_message": reason})
    emit({"decision": "continue" if AGENT == "antigravity" else "block", "reason": reason})


DEFAULT_OUT = {  # tools that need a JSON answer even when we have nothing to say
    "antigravity": {"pre_tool": {"decision": "allow"}},
    "cursor": {"pre_tool": {"permission": "allow"}, "prompt": {"continue": True}},
}


# --------------------------------------------------------------- normalise
def _path_from(ws):
    if isinstance(ws, dict):
        ws = ws.get("path") or ws.get("uri") or ""
    ws = str(ws or "")
    if ws.startswith("file://"):
        ws = ws[7:]
        if IS_WIN and re.match(r"^/[A-Za-z]:", ws):
            ws = ws[1:]
    return ws


def _json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return {"command": v}
    return v or {}


def normalize_cursor(raw):
    ev = raw.get("hook_event_name", "")
    roots = raw.get("workspace_roots") or []
    cwd = raw.get("cwd") or (_path_from(roots[0]) if roots else os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
    d = {"session_id": raw.get("conversation_id") or raw.get("session_id"),
         "transcript_path": raw.get("transcript_path"), "cwd": cwd, "prompt": raw.get("prompt", ""),
         "source": "startup", "loop_count": raw.get("loop_count", 0)}
    if ev in ("beforeShellExecution", "afterShellExecution"):
        d.update(tool_name="Bash", tool_input={"command": raw.get("command", ""), "workdir": raw.get("cwd")})
    elif ev == "afterFileEdit":
        edits = raw.get("edits") or []
        new = len(edits) == 1 and not edits[0].get("old_string")
        d.update(tool_name="Write" if new else "Edit", tool_input={"file_path": raw.get("file_path")})
    elif ev in ("preToolUse", "postToolUse"):
        tn, ti = raw.get("tool_name"), _json(raw.get("tool_input"))
        if tn == "Read":
            off = ti.get("offset") or ti.get("start_line_one_indexed")
            lim = ti.get("limit")
            end = ti.get("end_line_one_indexed_inclusive")
            if lim is None and end and off:
                lim = int(end) - int(off) + 1
            d.update(tool_name="Read", tool_input={
                "file_path": ti.get("file_path") or ti.get("path") or ti.get("target_file"),
                "offset": off, "limit": lim})
        elif tn == "Shell":
            d.update(tool_name="Bash", tool_input={"command": ti.get("command", ""), "workdir": raw.get("cwd")})
        else:
            d.update(tool_name=tn, tool_input=ti)
    return d


def normalize(raw):
    """Antigravity / Cursor -> the Claude/Codex shape everything else uses."""
    if AGENT == "cursor":
        return normalize_cursor(raw)
    if AGENT != "antigravity":
        return raw
    ws = raw.get("workspacePaths") or []
    tc = raw.get("toolCall") or {}
    args = tc.get("args") or {}
    name = AG_TOOLS.get(tc.get("name"), tc.get("name"))
    ti = {}
    if name == "Read":
        ti = {"file_path": args.get("AbsolutePath")}
        if args.get("StartLine") or args.get("EndLine"):
            start = int(args.get("StartLine") or 1)
            end = args.get("EndLine")
            ti.update(offset=start, limit=(int(end) - start + 1) if end else 2000)
    elif name in ("Write", "Edit"):
        ti = {"file_path": args.get("TargetFile")}
    elif name == "Bash":
        ti = {"command": args.get("CommandLine", ""), "workdir": args.get("Cwd")}
    return {"session_id": raw.get("conversationId"), "transcript_path": raw.get("transcriptPath"),
            "cwd": _path_from(ws[0]) if ws else os.getcwd(), "tool_name": name,
            "tool_input": ti, "prompt": raw.get("lastUserInput") or "", "source": "startup"}


def shell_cmd(ti):
    c = ti.get("command") if isinstance(ti, dict) else ti
    if isinstance(c, list):
        c = c[2] if len(c) >= 3 and str(c[0]).endswith(("bash", "sh", "zsh")) and c[1] in ("-lc", "-c") else " ".join(map(str, c))
    c = (c or "").strip()
    m = re.match(r"""^(?:ba|z)?sh\s+-l?c\s+(["'])(.*)\1$""", c, re.S)
    return m.group(2).strip() if m else c


def resolve(data, ti, path):
    p = Path(os.path.expanduser(path))
    if not p.is_absolute():
        base = (ti.get("workdir") if isinstance(ti, dict) else None) or data.get("cwd") or os.getcwd()
        p = Path(base) / p
    return str(p)


# ------------------------------------------------------------------ helpers
def head(path, n):
    text = strip_comments(read_text(path)).strip()
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("# ")]
    if len(lines) > n:
        lines = lines[:n] + [f"...(+{len(lines) - n} lines in {Path(path).name})"]
    return "\n".join(lines)


def tail(path, n):
    lines = [ln for ln in strip_comments(read_text(path)).splitlines() if ln.strip().startswith("-")]
    return "\n".join(lines[-n:])


def log_partial(proj, fp, start, count):
    r = rel(proj, fp)
    if not r:
        return
    lines = read_text(fp).splitlines(keepends=True)
    part = lines[max(start - 1, 0):max(start - 1, 0) + count]
    saved = est_tokens(sum(map(len, lines)) - sum(map(len, part)))
    if saved >= 100:
        log_event(proj, "saved", f"partial read {r} ({len(part)}/{len(lines)} lines)", saved, agent=AGENT)


def on_edit(proj, st, fp, is_new):
    r = rel(proj, fp)
    if not r:
        return
    p = Path(proj) / r
    if r.startswith(".ai/"):
        if p.name == "PROGRESS.md":
            st["edits_since_progress"] = 0
        if p.name == "CODEMAP.md":
            cm = read_text(p)
            st["pending_map"] = [f for f in st.get("pending_map", []) if f not in cm]
        return
    if r.startswith((".claude/", ".codex/", ".agents/")):
        return
    st["edits_since_progress"] = st.get("edits_since_progress", 0) + 1
    symbols.update_file(proj, p)
    if is_new and p.suffix.lower() in CODE_EXT and "test" not in p.name.lower():
        cm = read_text(Path(proj) / ".ai" / "CODEMAP.md")
        if r not in cm and r not in st.get("pending_map", []):
            st.setdefault("pending_map", []).append(r)
    log_event(proj, "edit", r, agent=AGENT)


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
    parts.append("Locate code: .ai/CODEMAP.md -> grep -n '<name>' .ai/symbols.txt -> read only that line range.")
    save_state(data.get("session_id"), {"edits_since_progress": 0, "pending_map": [], "clear_warned_at": 0})
    add_context("SessionStart", "\n\n".join(parts))


# ------------------------------------------------------- UserPromptSubmit / PreInvocation
def prompt(data, proj):
    sid = data.get("session_id")
    st = load_state(sid)
    text = data.get("prompt", "")
    if AGENT == "antigravity":  # PreInvocation fires before every model call: act once per user message
        if text == st.get("last_input"):
            return
        st["last_input"] = text
    notes = []
    ctx = session_usage(data.get("transcript_path"))["context"]
    if ctx >= cfg("CLEAR_AT", 80000) and ctx >= st.get("clear_warned_at", 0) + 30000:
        st["clear_warned_at"] = ctx
        notes.append(
            f"[code-assist] Context is ~{ctx // 1000}k tokens (expensive: every message re-sends it). "
            "When this task is done: overwrite .ai/PROGRESS.md (<=12 lines) and run "
            f"{LOG} done \"<one line>\", then end your reply with: "
            "\"✅ Progress saved — start a fresh chat (/clear) to continue cheaply; memory reloads automatically.\"")
        log_event(proj, "optimize", f"context hit {ctx // 1000}k -> saved progress & suggested /clear", agent=AGENT)
    if CORRECTION_RE.search(text):
        notes.append(
            "[code-assist] If this message corrects you or states a preference/habit, record it once: "
            f"{LOG} learn \"<lesson>\" (add --global if it applies to all projects). Skip if already recorded.")
    if AGENT == "cursor":  # beforeSubmitPrompt can't add context: deliver these at stop
        st["pending_notes"] = notes
        save_state(sid, st)
        return
    save_state(sid, st)
    if notes:
        add_context("UserPromptSubmit", "\n".join(notes))


# ----------------------------------------------------------------- PreToolUse
def pre_tool(data, proj):
    tool = data.get("tool_name")
    ti = data.get("tool_input") or {}
    if tool == "Read":
        fp, ranged = ti.get("file_path"), bool(ti.get("offset") or ti.get("limit"))
        if AGENT == "antigravity":
            how, full = "view_file with StartLine/EndLine (~±40 lines)", "view_file with StartLine=1 and EndLine={n}"
        else:
            how, full = "Read with offset/limit (~±40 lines)", "call Read again with limit={n}"
    elif tool == "Bash":
        m = WHOLE_READ.match(shell_cmd(ti))
        if not m:
            return
        fp, ranged = resolve(data, ti, m.group(2)), False
        how, full = "sed -n 'A,Bp' <file> (~±40 lines) or rg -n first", "run sed -n '1,{n}p' <file>"
    else:
        return
    r = rel(proj, fp) if fp else None
    if not r:
        return
    p = Path(fp)
    if p.suffix.lower() in BINARY_EXT or not p.is_file():
        return
    if is_generated(r):
        size = p.stat().st_size
        log_event(proj, "saved", f"blocked read of generated/vendor file {r}", est_tokens(size), agent=AGENT)
        deny(f"[code-assist] {r} is generated/vendor code (~{est_tokens(size)} tokens). "
             "Search it for the exact thing you need (grep/rg) instead of reading it.")
    if ranged:
        return
    text = read_text(p)
    n = text.count("\n") + 1
    if n <= cfg("BIG_FILE_LINES", 300):
        return
    deny(f"[code-assist] {r} has {n} lines (~{est_tokens(len(text))} tokens). Don't read it whole. "
         f"Symbols (line: kind name):\n{symbols.outline(proj, p)}\n"
         f"Read only the range you need: {how}. If you truly need the entire file, {full.format(n=n)}.")


# ---------------------------------------------------------------- PostToolUse
def post_tool(data, proj):
    tool = data.get("tool_name")
    ti = data.get("tool_input") or {}
    sid = data.get("session_id")
    st = load_state(sid)
    if tool == "Read":
        if ti.get("offset") or ti.get("limit"):
            log_partial(proj, ti.get("file_path", ""), int(ti.get("offset") or 1), int(ti.get("limit") or 2000))
    elif tool == "Bash":
        c = shell_cmd(ti)
        m = SED_READ.match(c)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            log_partial(proj, resolve(data, ti, m.group(4)), a, max(b - a + 1, 0))
        m = HEAD_READ.match(c)
        if m:
            log_partial(proj, resolve(data, ti, m.group(3)), 1, int(m.group(1)))
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        fp = ti.get("file_path") or ti.get("notebook_path")
        if fp:
            on_edit(proj, st, fp, tool == "Write")
    elif tool == "apply_patch":  # Codex
        patch = shell_cmd(ti)
        for op, path in PATCH_FILE.findall(patch):
            on_edit(proj, st, resolve(data, ti, path), op == "Add")
        for path in PATCH_MOVE.findall(patch):
            on_edit(proj, st, resolve(data, ti, path), True)
    save_state(sid, st)


# ----------------------------------------------------------------------- Stop
def stop(data, proj):
    record_usage(data, proj)
    sid = data.get("session_id")
    st = load_state(sid)
    if AGENT == "antigravity":  # no stop_hook_active: ask at most once per user message
        if st.get("stop_asked_for") == data.get("prompt", "") and "stop_asked_for" in st:
            return
    elif data.get("stop_hook_active") or (AGENT == "cursor" and data.get("loop_count")):
        return
    cm = read_text(proj / ".ai" / "CODEMAP.md")
    pend = [f for f in st.get("pending_map", []) if f not in cm and (proj / f).exists()]
    todo, what = [], []
    if pend:
        todo.append("add to .ai/CODEMAP.md (1 line each: feature -> file -> main symbols): " + ", ".join(pend[:10]))
        what.append(f"CODEMAP +{len(pend)} files")
    st["pending_map"] = []  # ask once per batch
    if st.get("edits_since_progress", 0) >= cfg("PROGRESS_EVERY", 4):
        todo.append(f"overwrite .ai/PROGRESS.md (<=12 lines: done / in progress / next / open issues) and run {LOG} done \"<one line summary>\"")
        what.append("PROGRESS/HISTORY")
        st["edits_since_progress"] = 0
    if AGENT == "cursor" and st.get("pending_notes"):
        todo += [n.replace("[code-assist] ", "") for n in st.pop("pending_notes")]
        what.append("delivered notes")
    if todo and AGENT == "antigravity":
        st["stop_asked_for"] = data.get("prompt", "")
    save_state(sid, st)
    if todo:
        log_event(proj, "optimize", "auto memory update: " + ", ".join(what), agent=AGENT)
        block_stop("[code-assist] Before finishing, quietly do this (no explanation to the user): "
                   + "; ".join(todo) + ". Then stop.")


# ----------------------------------------------------------------- SessionEnd
def session_end(data, proj):
    record_usage(data, proj)
    drop_state(data.get("session_id"))


HANDLERS = {"session_start": session_start, "prompt": prompt, "pre_tool": pre_tool,
            "post_tool": post_tool, "stop": stop, "session_end": session_end}


def main():
    global AGENT
    utf8_stdio()
    args = sys.argv[1:]
    if "--agent" in args and args.index("--agent") + 1 < len(args):
        AGENT = args[args.index("--agent") + 1]
    event = args[0] if args else ""
    try:
        raw = json.load(sys.stdin)
    except ValueError:
        raw = {}
    if AGENT == "claude" and "cursor_version" in raw:
        sys.exit(0)  # Cursor running the Claude config (third-party mode): the --agent cursor hooks handle it
    try:
        data = normalize(raw)
        proj = project_dir(data)
        if event in HANDLERS and (proj / ".ai").is_dir():
            HANDLERS[event](data, proj)
    except SystemExit:
        pass
    except Exception as e:  # never break the user's session
        try:
            STORE.mkdir(parents=True, exist_ok=True)
            with open(STORE / "errors.log", "a", encoding="utf-8") as f:
                f.write(f"{AGENT}/{event}: {e!r}\n")
        except OSError:
            pass
    finally:
        if AGENT in DEFAULT_OUT and not EMITTED:  # these tools expect JSON every time
            print(json.dumps(DEFAULT_OUT[AGENT].get(event, {})))
    sys.exit(0)


if __name__ == "__main__":
    main()
