---
name: token-saver
description: Auto-manages project memory to cut token usage — installs per-project memory files (CODEMAP, PATTERNS, PROGRESS, LEARNINGS, HISTORY), a symbol index (name -> file:line) and hooks that block wasteful reads, keep docs updated, learn the user's preferences and track tokens used/saved. Use when the user says "/token-saver", "install token saver", "setup project memory", "token report", "koto token save holo", "aj ki optimize korecho/ki shikhecho", "sync codemap", or starts work in a project that has no .ai/ folder and asks to save tokens.
---

# token-saver

Skill dir: `~/.claude/skills/token-saver` (below: `$TS`). Hooks do the automatic part; you do the
thinking part (writing CODEMAP/PATTERNS, compacting docs). Be brief with the user — report results,
not process. Reply in the user's language.

Arguments: `init` (default if `.ai/` is missing), `sync`, `report [--days N] [--all]`, `learn "<text>"`, `status`.

## init — install into the current project
1. Run `bash ~/.claude/skills/token-saver/install.sh "$PWD"` and read its output.
2. **Existing project** (installer says EXISTING): build the map once, cheaply:
   - Structure: `git ls-files 2>/dev/null | head -400` (or `find . -type f` excluding junk dirs).
   - Symbols per file: `cut -f3 .ai/symbols.txt | cut -d: -f1 | sort | uniq -c | sort -rn | head -80`
     and `grep -v method .ai/symbols.txt | head -300`.
   - Read only manifests (package.json, pubspec.yaml, composer.json, requirements.txt…) and at most
     2–3 representative files with offset/limit. Do NOT read the codebase file by file.
   - Write `.ai/CODEMAP.md` grouped by feature: `- <feature> -> <path> -> <main symbols>` (≤150 lines,
     no line numbers). Write `.ai/PATTERNS.md`: stack, run/test/lint commands, folder layout,
     naming, state/data/API conventions (≤40 lines).
   - If an old CLAUDE.md has long docs duplicated in CODEMAP/PATTERNS, offer to slim it (ask first).
3. **New project**: leave the templates; they fill up as you work. Add the stack to PATTERNS once chosen.
4. `python3 $TS/scripts/log.py optimize "init: CODEMAP <n> lines, PATTERNS <n> lines"`.
5. Tell the user: done, and **start a new Claude session in this folder** so the hooks load.

## sync — refresh memory (run after big changes, pulls, or weekly)
1. `python3 $TS/scripts/symbols.py "$PWD"` (rebuild index).
2. Changes since last sync: `git log --oneline -20`, `git diff --stat $(cat .ai/.last_sync 2>/dev/null || echo HEAD~20) HEAD`.
   Update CODEMAP for added/removed/renamed files; delete lines whose files no longer exist
   (check with `test -e`). Then `git rev-parse HEAD > .ai/.last_sync`.
3. Compact: merge duplicate/contradicting lines in LEARNINGS.md and PATTERNS.md (newest wins);
   move learnings that are really personal habits (language, tone, style) to
   `~/.claude/token-saver/USER_PATTERNS.md`; keep PROGRESS ≤12 lines.
4. If any source file is > 600 lines, list them as split candidates (don't split without asking).
5. Log what you did: `python3 $TS/scripts/log.py optimize "sync: ..."`. Report in 3–5 lines.

## report
Run `python3 $TS/scripts/report.py [--days N] [--all]` and show the output as-is, then add at most
2 lines of advice based on it (e.g. low cache hit rate -> clear less often mid-task; many blocked
reads -> CODEMAP is missing areas, run sync).

## learn
`python3 $TS/scripts/log.py learn "<text>"` (add `--global` for cross-project habits). Confirm in one line.

## status
Show: is `.ai/` present, line counts of the .ai files (`wc -l .ai/*.md`), symbol count,
whether hooks are in `.claude/settings.json` (`grep -c token-saver .claude/settings.json`).

## What runs automatically (hooks, no prompting needed)
- SessionStart (startup / after /clear / after compact): injects PROGRESS, last HISTORY lines,
  LEARNINGS and global USER_PATTERNS — so `/clear` loses nothing.
- Read of a file > 300 lines without offset/limit -> blocked with that file's symbol outline
  (line numbers), so you jump straight to the right range. Vendor/lock/generated files blocked.
- Every edit -> symbol index for that file refreshed; new files queued for CODEMAP.
- Stop -> if new files are unmapped or ≥4 edits since last PROGRESS, you're asked to update them.
- Context ≥ 80k tokens -> you save progress and tell the user to /clear.
- User message looks like a correction/preference -> you're nudged to `log.py learn` it.
- Usage per session (input/output/cache) recorded for the report.
Tuning env vars: `TOKEN_SAVER_BIG_FILE_LINES` (300), `TOKEN_SAVER_CLEAR_AT` (80000),
`TOKEN_SAVER_PROGRESS_EVERY` (4).

## Uninstall from a project
Remove the token-saver entries from `.claude/settings.json`, the `token-saver:start…end` block in
CLAUDE.md, and optionally `.ai/`. Ask before deleting `.ai/` (it holds the user's notes).
