---
name: code-assist
description: Coding assistant memory manager that cuts token usage automatically — installs per-project memory (CODEMAP, PATTERNS, PROGRESS, LEARNINGS, HISTORY), a symbol index (name -> file:line), AGENTS.md for other AI tools, and hooks that block wasteful reads, keep docs updated, learn the user's preferences and track tokens used/saved. Use when the user says "/code-assist", "install code assist", "setup project memory", "token report", "koto token save holo", "aj ki optimize korecho / ki shikhecho", "sync codemap", or asks to save tokens in a project without a .ai/ folder.
---

# code-assist

Skill dir `$CA` = `~/.claude/skills/code-assist`. Python command `<py>` = the one at the top of the
"Memory" commands in `.ai/RULES.md` (python3 on macOS/Linux, usually `python` or `py -3` on Windows).
Works the same on macOS, Linux and Windows, in Claude Code, OpenAI Codex and Google Antigravity
(other agents read the same memory via AGENTS.md). Hooks do the automatic part; you do the
thinking part. If you can't run shell commands, do the steps by editing the files directly. Be brief with the user — report results, not process. Reply in the user's language.

Arguments: `init` (default if `.ai/` is missing), `sync`, `report [--days N] [--all]`, `learn "<text>"`, `status`.

## init — install into the current project
1. Run `bash ~/.claude/skills/code-assist/install.sh "$PWD"` and read its output.
   (Add `--no-agents` only if the user doesn't want an AGENTS.md.)
2. **Existing project** (output says EXISTING): build the map once, cheaply:
   - Structure: `git ls-files 2>/dev/null | head -400` (or `find` excluding junk dirs).
   - Symbols per file: `cut -f3 .ai/symbols.txt | cut -d: -f1 | sort | uniq -c | sort -rn | head -80`
     and `grep -v method .ai/symbols.txt | head -300`.
   - Read only manifests (package.json, pubspec.yaml, composer.json, requirements.txt…) and at most
     2–3 representative files with offset/limit. Do NOT read the codebase file by file.
   - Write `.ai/CODEMAP.md` grouped by feature: `- <feature> -> <path> -> <main symbols>` (≤150 lines,
     no line numbers). Write `.ai/PATTERNS.md`: stack, run/test/lint commands, folder layout,
     naming, state/data/API conventions (≤40 lines).
   - If an old CLAUDE.md has long docs duplicated in CODEMAP/PATTERNS, offer to slim it (ask first).
3. **New project**: leave the templates; they fill up as you work. Add the stack to PATTERNS once chosen.
4. `<py> $CA/scripts/log.py optimize "init: CODEMAP <n> lines, PATTERNS <n> lines"`.
5. Tell the user: done, and **start a new chat/session in this folder** so the hooks load.
   Codex and Antigravity hooks are global (installed by setup); Cursor, Copilot, Gemini CLI… use AGENTS.md.

## sync — refresh memory (after big changes, `git pull`, or weekly)
1. `<py> $CA/scripts/symbols.py "$PWD"` (rebuild index).
2. Changes since last sync: `git log --oneline -20`, `git diff --stat $(cat .ai/.last_sync 2>/dev/null || echo HEAD~20) HEAD`.
   Update CODEMAP for added/removed/renamed files; delete lines whose files no longer exist.
   Then `git rev-parse HEAD > .ai/.last_sync`.
3. Compact: merge duplicate/contradicting lines in LEARNINGS.md and PATTERNS.md (newest wins);
   move personal habits (language, tone, style) to `~/.claude/code-assist/USER_PATTERNS.md`;
   keep PROGRESS ≤12 lines.
4. List source files > 600 lines as split candidates (don't split without asking).
5. `<py> $CA/scripts/log.py optimize "sync: ..."`. Report in 3–5 lines.

## report
Run `<py> $CA/scripts/report.py [--days N] [--all]` and show the output as-is, then at most 2 lines
of advice (low cache hit rate -> avoid /clear mid-task; many blocked reads -> run sync).

## learn
`<py> $CA/scripts/log.py learn "<text>"` (`--global` for cross-project habits). Confirm in one line.

## status
Show: `.ai/` present?, `wc -l .ai/*.md`, symbol count (`wc -l .ai/symbols.txt`),
hooks present (`grep -c code-assist .claude/settings.json`), AGENTS.md present?

## What runs automatically (hooks: Claude Code, Codex, Antigravity)
- SessionStart (startup / after /clear / after compact): injects PROGRESS, last HISTORY lines,
  LEARNINGS and global USER_PATTERNS — so `/clear` loses nothing.
- Reading a file > 300 lines whole (Read / view_file / `cat`, `nl`) -> blocked with that file's
  symbol outline (line numbers). Vendor/lock/generated files blocked.
- Every edit (Edit/Write, Codex apply_patch, Antigravity write/replace) -> symbol index refreshed; new files queued for CODEMAP.
- Stop -> unmapped new files or ≥4 edits since last PROGRESS -> you're asked to update them.
- Context ≥ 80k tokens -> save progress and tell the user to /clear.
- User message looks like a correction/preference -> you're nudged to `log.py learn` it.
- Usage per session (input/output/cache) recorded for the report (Claude Code and Codex; Antigravity: savings only).
Tuning env vars: `CODE_ASSIST_BIG_FILE_LINES` (300), `CODE_ASSIST_CLEAR_AT` (80000),
`CODE_ASSIST_PROGRESS_EVERY` (4).

## Uninstall from a project
Remove the code-assist entries from `.claude/settings.json`, the `code-assist:start…end` blocks in
CLAUDE.md and AGENTS.md, and optionally `.ai/`. Ask before deleting `.ai/` (it holds the user's notes).
