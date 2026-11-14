# token-saver — a Claude Code skill that cuts token usage automatically

Claude reads your project once, keeps a **map** (feature → file → function) and a **symbol index**
(function → `file:line`), and from then on jumps straight to the right lines instead of re-reading
whole files. It also remembers progress across `/clear`, learns your preferences, and reports how
many tokens you used and saved.

## Install (any Mac / Linux PC)

```bash
curl -fsSL https://raw.githubusercontent.com/arifbiswas/claude-token-saver/main/setup.sh | bash
```

Same command again = **update**. Requires `git` and `python3` (no other dependencies).
Windows: use WSL or Git Bash.

## Use in a project (new or existing)

In Claude Code, inside the project:

```
/token-saver init
```

Then **start a new Claude session** in that folder so the hooks load. Done — everything else is automatic.

| Command | What it does |
|---|---|
| `/token-saver init` | Install into this project; for existing code, builds CODEMAP + PATTERNS once |
| `/token-saver report` | Today's tokens used / saved, optimizations, what it learned (`--days 7`, `--all`) |
| `/token-saver sync` | Refresh map after big changes or `git pull`, compact memory files |
| `/token-saver learn "…"` | Teach a rule manually (`--global` = all projects) |
| `/token-saver status` | Check the setup |

## What it adds to a project

```
CLAUDE.md                 + imports .ai/RULES.md and .ai/PATTERNS.md (your content kept)
.claude/settings.json     + hooks, + deny rules for node_modules / build / lock files
.ai/CODEMAP.md            feature -> file -> symbols  (no line numbers, they go stale)
.ai/symbols.txt           name -> file:line, auto-updated on every edit (git-ignored)
.ai/PATTERNS.md           stack, commands, conventions
.ai/PROGRESS.md           where you left off (overwritten, ≤12 lines)
.ai/HISTORY.md            dated one-line changelog
.ai/LEARNINGS.md          corrections & preferences for this project
~/.claude/token-saver/    global preferences, usage stats, event log
```

## What happens automatically

- **Session start / after `/clear`** → progress, recent history and learnings are injected, so clearing loses nothing.
- **Reading a file > 300 lines without a range** → blocked, and Claude gets that file's function list with line numbers, so it reads only the part it needs.
- **Reading vendor / lock / generated files** → blocked.
- **Every edit** → symbol index updated; new files queued for CODEMAP.
- **After ~4 edits** → PROGRESS and HISTORY updated.
- **Context ≥ 80k tokens** → progress saved and Claude tells you to type `/clear`.
- **You correct it** ("don't…", "always…", "eivabe na", "ভুল") → the lesson is saved.
- **Every turn** → token usage recorded for the report.

Tuning (env vars): `TOKEN_SAVER_BIG_FILE_LINES=300`, `TOKEN_SAVER_CLEAR_AT=80000`, `TOKEN_SAVER_PROGRESS_EVERY=4`.

## Limits (honest)

- `/clear` must be typed by you — hooks can't run it. Claude reminds you at the right time.
- "Saved" numbers are estimates (full file size vs. the part actually read). "Used" numbers come from Claude Code's own usage data.
- The symbol index is regex-based: good for JS/TS/React, Python, Dart/Flutter, PHP/Laravel, Go; may miss exotic syntax.
- Hook errors never block your session; they go to `~/.claude/token-saver/errors.log`.

## Uninstall

Per project: remove the `token-saver` hook entries from `.claude/settings.json`, the
`token-saver:start … end` block from `CLAUDE.md`, and (optionally) `.ai/`.
Skill: `rm -rf ~/.claude/skills/token-saver`.

---

### বাংলায় সংক্ষেপে

1. যেকোনো PC-তে উপরের `curl …` command চালাও, skill install হয়ে যাবে।
2. Project খুলে Claude-এ `/token-saver init` লেখো, তারপর নতুন session খোলো।
3. এরপর সব automatic: AI পুরো file না পড়ে সরাসরি দরকারি line-এ যাবে, progress মনে রাখবে, তোমার pattern শিখবে।
4. হিসাব দেখতে: `/token-saver report`

MIT License.
