"""Shared helpers for token-saver (hooks, logger, report, indexer)."""
import datetime
import json
import os
import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
STORE = Path(os.path.expanduser("~/.claude/token-saver"))
EVENTS = STORE / "events.jsonl"
SESS_DIR = STORE / "sessions"
STATE_DIR = STORE / "state"
USER_PATTERNS = STORE / "USER_PATTERNS.md"

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", ".output", "out",
    "coverage", ".dart_tool", "Pods", "vendor", ".venv", "venv", "__pycache__",
    ".gradle", ".idea", ".vscode", ".turbo", ".cache", ".expo", "DerivedData",
    "storage", ".svelte-kit", "target", ".ai",
}
LOCK_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pubspec.lock",
    "composer.lock", "Podfile.lock", "Cargo.lock", "poetry.lock", "bun.lockb",
    "Gemfile.lock",
}
GENERATED_SUFFIXES = (".min.js", ".min.css", ".map", ".g.dart", ".freezed.dart")
CODE_EXT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".py",
    ".dart", ".php", ".go", ".rb", ".java", ".kt", ".swift", ".rs", ".cs",
}
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf", ".zip",
    ".mp4", ".mov", ".mp3", ".woff", ".woff2", ".ttf", ".otf", ".ipynb",
}


def cfg(name, default):
    try:
        return int(os.environ.get("TOKEN_SAVER_" + name, default))
    except ValueError:
        return default


def find_project(start=None):
    """Nearest folder (walking up) that has a .ai/ directory."""
    p = Path(start or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".ai").is_dir():
            return cand
    return None


def project_dir(data=None):
    p = os.environ.get("CLAUDE_PROJECT_DIR") or (data or {}).get("cwd") or os.getcwd()
    return find_project(p) or Path(p).resolve()


def today():
    return datetime.date.today().isoformat()


def est_tokens(chars):
    return int(chars / 4)


def rel(proj, path):
    try:
        return str(Path(path).resolve().relative_to(proj))
    except ValueError:
        return None


def is_generated(relpath):
    parts = Path(relpath).parts
    name = parts[-1] if parts else ""
    return (any(x in IGNORE_DIRS for x in parts[:-1]) or name in LOCK_FILES
            or name.endswith(GENERATED_SUFFIXES))


def read_text(path, limit_bytes=2_000_000):
    try:
        p = Path(path)
        if p.stat().st_size > limit_bytes:
            return ""
        return p.read_text(errors="ignore")
    except OSError:
        return ""


def log_event(proj, type_, detail="", tokens=0, **extra):
    STORE.mkdir(parents=True, exist_ok=True)
    ev = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "date": today(), "project": str(proj), "type": type_,
        "tokens": int(tokens), "detail": detail,
    }
    ev.update(extra)
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def read_events():
    out = []
    try:
        with open(EVENTS, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def _state_path(sid):
    safe = re.sub(r"[^A-Za-z0-9_-]", "", sid or "default") or "default"
    return STATE_DIR / f"{safe}.json"


def load_state(sid):
    try:
        return json.loads(_state_path(sid).read_text())
    except (OSError, ValueError):
        return {"edits_since_progress": 0, "pending_map": [], "clear_warned_at": 0}


def save_state(sid, st):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(sid).write_text(json.dumps(st))


def drop_state(sid):
    try:
        _state_path(sid).unlink()
    except OSError:
        pass


def session_usage(transcript_path):
    """Token usage per local date + current context size, from a Claude Code transcript."""
    by_msg = {}
    last_ctx = 0
    if not transcript_path:
        return {"by_date": {}, "context": 0}
    try:
        f = open(os.path.expanduser(transcript_path), encoding="utf-8")
    except OSError:
        return {"by_date": {}, "context": 0}
    with f:
        for line in f:
            if '"usage"' not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            msg = e.get("message") or {}
            u = msg.get("usage")
            if e.get("type") != "assistant" or not u:
                continue
            mid = msg.get("id") or e.get("uuid")
            by_msg[mid] = (e.get("timestamp", ""), u)
            if not e.get("isSidechain"):
                last_ctx = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                            + u.get("cache_creation_input_tokens", 0))
    by_date = {}
    for ts, u in by_msg.values():
        try:
            d = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date().isoformat()
        except ValueError:
            d = today()
        b = by_date.setdefault(d, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "turns": 0})
        b["input"] += u.get("input_tokens", 0)
        b["output"] += u.get("output_tokens", 0)
        b["cache_read"] += u.get("cache_read_input_tokens", 0)
        b["cache_write"] += u.get("cache_creation_input_tokens", 0)
        b["turns"] += 1
    return {"by_date": by_date, "context": last_ctx}


def record_usage(data, proj):
    sid = data.get("session_id")
    if not sid:
        return None
    u = session_usage(data.get("transcript_path"))
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    (SESS_DIR / f"{re.sub(r'[^A-Za-z0-9_-]', '', sid)}.json").write_text(
        json.dumps({"project": str(proj), "by_date": u["by_date"]}))
    return u


def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)
