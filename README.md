# code-assist — AI coding memory that cuts token usage automatically

Your AI reads the project once, keeps a **map** (feature → file → function) and a **symbol index**
(function → `file:line`), and from then on jumps straight to the right lines instead of re-reading
whole files. It remembers progress across `/clear`, learns your preferences, and reports how many
tokens you used and saved.

Works on **macOS, Linux and Windows**, with full automation in **Claude Code, OpenAI Codex and
Google Antigravity**. The same memory is shared with Cursor, GitHub Copilot, Gemini CLI and other agents via `AGENTS.md`.

| | Claude Code | Codex | Antigravity | Cursor / Copilot / others |
|---|---|---|---|---|
| Memory (`.ai/` + AGENTS.md) | ✅ | ✅ | ✅ | ✅ |
| `code-assist` skill | ✅ `/code-assist` | ✅ `$code-assist` | ✅ `/code-assist` or name it | – |
| Auto hooks (block big reads, auto-docs, learning) | ✅ per project | ✅ global | ✅ global | – |
| Token usage in report | ✅ | ✅ | savings only | – |

`setup` links the skill into `~/.agents/skills` (Codex) and `~/.gemini/config/skills` (Antigravity) and
adds their global hooks, but only if that tool is installed. Re-run setup after installing a new tool.

## Install the skill (once per PC)

**macOS / Linux / Windows Git Bash**
```bash
git clone https://github.com/arifbiswas/code-assist.git ~/.claude/skills/code-assist
bash ~/.claude/skills/code-assist/setup.sh
```

**Windows PowerShell**
```powershell
git clone https://github.com/arifbiswas/code-assist.git "$HOME\.claude\skills\code-assist"
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\setup.ps1"
```

**Update** later: run just the second line again (`setup.sh` / `setup.ps1` pulls the latest version).
Needs `git` and Python 3.8+ (nothing else). No remote script is piped into your shell: you get a normal git clone you can read first.

## Use in a project (new or existing)

Ask your AI, inside the project:
```
/code-assist init        (Claude Code, Antigravity)
$code-assist init        (Codex)
```
Then **start a new chat/session** in that folder so the hooks load. Everything else is automatic.
In Codex, approve the hooks once with `/hooks` (Codex asks you to review new hooks).

Without Claude (terminal):
```bash
bash ~/.claude/skills/code-assist/install.sh /path/to/project
```
```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\install.ps1" -Project C:\path\to\project
```

| Command | What it does |
|---|---|
| `/code-assist init` | Install into this project; for existing code, builds CODEMAP + PATTERNS once |
| `/code-assist report` | Tokens used / saved today, optimizations, what it learned (`--days 7`, `--all`) |
| `/code-assist sync` | Refresh the map after big changes or `git pull`, compact memory files |
| `/code-assist learn "…"` | Teach a rule manually (`--global` = all projects) |
| `/code-assist status` | Check the setup |

## What it adds to a project

```
CLAUDE.md                 + imports .ai/RULES.md and .ai/PATTERNS.md (your content kept)
AGENTS.md                 + short memory block for Cursor / Codex / Copilot / Gemini … (skip: --no-agents)
.claude/settings.json     + hooks, + deny rules for node_modules / build / lock files
.ai/CODEMAP.md            feature -> file -> symbols (no line numbers, they go stale)
.ai/symbols.txt           name -> file:line, auto-updated on every edit (git-ignored)
.ai/PATTERNS.md           stack, commands, conventions
.ai/PROGRESS.md           where you left off (overwritten, ≤12 lines)
.ai/HISTORY.md            dated one-line changelog
.ai/LEARNINGS.md          corrections & preferences for this project
~/.claude/code-assist/    global preferences, usage stats, event log
```

## What happens automatically (Claude Code, Codex, Antigravity)

- **Session start / after `/clear`** → progress, recent history and learnings are injected, so clearing loses nothing.
- **Reading a file > 300 lines whole** (Read, `view_file`, `cat`, `nl`) → blocked; the AI gets that file's function list with line numbers and reads only what it needs.
- **Reading vendor / lock / generated files** → blocked.
- **Every edit** (Claude Edit/Write, Codex `apply_patch`, Antigravity write/replace) → symbol index updated; new files queued for CODEMAP.
- **After ~4 edits** → PROGRESS and HISTORY updated.
- **Context ≥ 80k tokens** → progress saved and you're told to type `/clear`.
- **You correct it** ("don't…", "always…", "eivabe na", "ভুল") → the lesson is saved.
- **Every turn** → token usage recorded for the report.

Agents without supported hooks (Cursor, Copilot, …) get guidance only: they read the same `.ai/` memory via `AGENTS.md`.
Codex and Antigravity hook support follows their official docs, but only the adapters have been tested, by simulating each tool's hook input. It hasn't been run inside those apps yet. Please report issues.

Tuning (env vars): `CODE_ASSIST_BIG_FILE_LINES=300`, `CODE_ASSIST_CLEAR_AT=80000`, `CODE_ASSIST_PROGRESS_EVERY=4`.

## Limits

- You type `/clear` yourself. Hooks can't run it, so Claude reminds you at the right time.
- "Saved" numbers are estimates (full file size vs. the part actually read). "Used" numbers come from Claude Code's own usage data.
- The symbol index is regex-based. It works well for JS/TS/React, Python, Dart/Flutter, PHP/Laravel and Go, but may miss exotic syntax.
- Hook errors never block your session. They're written to `~/.claude/code-assist/errors.log`.

## Upgrading from token-saver

Run the two install lines above. `setup.sh` / `setup.ps1` moves the old skill aside, and the next project install migrates your data. Then run
`/code-assist init` again in each project that used token-saver to update its hooks.

## Uninstall

Per project: remove the `code-assist` hook entries from `.claude/settings.json` and the
`code-assist:start … end` blocks from `CLAUDE.md` and `AGENTS.md`. You can also delete `.ai/`.
Global: remove the code-assist entries from `~/.codex/hooks.json` and the `"code-assist"` key from
`~/.gemini/config/hooks.json`, plus the links `~/.agents/skills/code-assist` and `~/.gemini/config/skills/code-assist`.
To remove the skill: `rm -rf ~/.claude/skills/code-assist`.

---

### বাংলায় সংক্ষেপে

1. যেকোনো PC-তে উপরের দুই line চালাও: `git clone`, তারপর `setup.sh` (Mac/Linux/Git Bash) বা `setup.ps1` (Windows PowerShell)।
2. Project খুলে Claude-এ `/code-assist init` লেখো, তারপর নতুন session খোলো।
3. এরপর সব automatic: AI পুরো file না পড়ে সরাসরি দরকারি line-এ যাবে, progress মনে রাখবে, তোমার pattern শিখবে।
4. Claude Code, Codex আর Antigravity তিনটাতেই automatic hooks চলে। Cursor বা Copilot `AGENTS.md` থেকে একই memory পড়বে।
5. হিসাব দেখতে: `/code-assist report`

MIT License.
