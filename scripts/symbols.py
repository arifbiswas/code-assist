#!/usr/bin/env python3
"""Symbol index: name -> file:line, stored in .ai/symbols.txt (one line per symbol).

  symbols.py <project>                 full rebuild
  symbols.py <project> <file>          re-index one file
  symbols.py <project> --outline <f>   print symbols of one file
Lookup: grep -n "calcTotal" .ai/symbols.txt
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CODE_EXT, IGNORE_DIRS, is_generated, read_text  # noqa: E402

KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "function", "else",
            "constructor", "super", "new", "typeof", "await", "with", "elif"}

ID = r"[A-Za-z_$][\w$]*"
JS = [
    ("fn", re.compile(rf"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*({ID})")),
    ("fn", re.compile(rf"^\s*(?:export\s+)?(?:const|let|var)\s+({ID})\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|{ID})\s*(?::[^=]+)?=>")),
    ("fn", re.compile(rf"^\s*(?:export\s+)?(?:const|let|var)\s+({ID})\s*=\s*(?:React\.)?(?:memo|forwardRef|useCallback|createSlice|createAsyncThunk|styled)\b")),
    ("class", re.compile(rf"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+({ID})")),
    ("type", re.compile(rf"^\s*(?:export\s+)?(?:declare\s+)?(?:interface|type|enum)\s+({ID})")),
    ("method", re.compile(rf"^\s{{2,}}(?:public\s+|private\s+|protected\s+|static\s+|async\s+|get\s+|set\s+)*({ID})\s*\([^)]*\)\s*(?::[^{{]+)?\{{\s*$")),
    ("route", re.compile(r"""^\s*(?:router|app|route|server)\.(get|post|put|patch|delete)\(\s*['"`]([^'"`]+)""")),
]
PY = [
    ("fn", re.compile(r"^\s*(?:async\s+)?def\s+(\w+)")),
    ("class", re.compile(r"^\s*class\s+(\w+)")),
    ("route", re.compile(r"""^\s*@\w+\.(get|post|put|patch|delete|route)\(\s*['"]([^'"]+)""")),
]
DART = [
    ("class", re.compile(r"^\s*(?:abstract\s+)?(?:class|mixin|enum|extension)\s+(\w+)")),
    ("fn", re.compile(r"^\s*(?:static\s+)?(?:Future|Stream|void|Widget|int|double|bool|String|dynamic|List|Map|[A-Z]\w*)(?:<[^>]*>)?\??\s+(\w+)\s*\([^;]*$")),
]
PHP = [
    ("class", re.compile(r"^\s*(?:abstract\s+|final\s+)?(?:class|interface|trait|enum)\s+(\w+)")),
    ("fn", re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+)*function\s+(\w+)")),
    ("route", re.compile(r"""^\s*Route::(get|post|put|patch|delete)\(\s*['"]([^'"]+)""")),
]
GO = [
    ("fn", re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)")),
    ("type", re.compile(r"^type\s+(\w+)")),
]
GENERIC = [
    ("class", re.compile(r"^\s*(?:public\s+|private\s+|internal\s+|data\s+|open\s+|final\s+)*(?:class|struct|interface|enum|protocol|object)\s+(\w+)")),
    ("fn", re.compile(r"^\s*(?:public\s+|private\s+|internal\s+|static\s+|override\s+|suspend\s+)*(?:fun|func|fn|def)\s+(\w+)")),
]

BY_EXT = {".js": JS, ".jsx": JS, ".ts": JS, ".tsx": JS, ".mjs": JS, ".cjs": JS,
          ".vue": JS, ".svelte": JS, ".py": PY, ".dart": DART, ".php": PHP, ".go": GO}


def index_file(path):
    ext = Path(path).suffix.lower()
    pats = BY_EXT.get(ext, GENERIC)
    out = []
    for i, line in enumerate(read_text(path, 600_000).splitlines(), 1):
        if len(line) > 300:
            continue
        for kind, rx in pats:
            m = rx.match(line)
            if not m:
                continue
            if kind == "route":
                name = f"{m.group(1).upper()} {m.group(2)}"
            else:
                name = m.group(1)
                if name in KEYWORDS:
                    continue
            out.append((name, kind, i))
            break
    return out


def walk(proj):
    for root, dirs, files in os.walk(proj):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not d.startswith("."))
        for fn in sorted(files):
            p = Path(root) / fn
            if p.suffix.lower() in CODE_EXT:
                r = str(p.relative_to(proj))
                if not is_generated(r) and "test" not in fn.lower():
                    yield p, r


def fmt(r, syms):
    return [f"{name}\t{kind}\t{r}:{line}" for name, kind, line in syms]


def index_path(proj):
    return Path(proj) / ".ai" / "symbols.txt"


def rebuild(proj):
    proj = Path(proj).resolve()
    lines = []
    count = 0
    for p, r in walk(proj):
        lines += fmt(r, index_file(p))
        count += 1
        if count > 5000:
            break
    index_path(proj).write_text("\n".join(lines) + ("\n" if lines else ""))
    return count, len(lines)


def update_file(proj, path):
    proj = Path(proj).resolve()
    p = Path(path).resolve()
    try:
        r = str(p.relative_to(proj))
    except ValueError:
        return
    if p.suffix.lower() not in CODE_EXT or is_generated(r):
        return
    idx = index_path(proj)
    old = idx.read_text().splitlines() if idx.exists() else []
    keep = [ln for ln in old if ln.split("\t")[-1].rsplit(":", 1)[0] != r]
    new = fmt(r, index_file(p)) if p.exists() else []
    idx.write_text("\n".join(keep + new) + "\n")


def outline(proj, path, limit=40):
    syms = index_file(path)
    rows = [f"  L{line:<5} {kind:<6} {name}" for name, kind, line in syms[:limit]]
    if len(syms) > limit:
        rows.append(f"  ... {len(syms) - limit} more (grep .ai/symbols.txt)")
    return "\n".join(rows) or "  (no symbols found — use grep -n)"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    proj = sys.argv[1]
    if len(sys.argv) == 2:
        files, syms = rebuild(proj)
        print(f"indexed {files} files, {syms} symbols -> .ai/symbols.txt")
    elif sys.argv[2] == "--outline":
        print(outline(proj, sys.argv[3]))
    else:
        update_file(proj, sys.argv[2])
