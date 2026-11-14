# Commands

There are two ways to use code-assist: ask your AI (skill commands), or run the scripts yourself
in a terminal. Both do the same thing.

- [Skill commands](#skill-commands): `init`, `sync`, `report`, `learn`, `status`
- [Terminal scripts](#terminal-scripts): `install`, `setup`, `report.py`, `log.py`, `symbols.py`
- [Reading the report](#reading-the-report)

How to call the skill in each tool:

| Tool | Syntax | Example |
|---|---|---|
| Claude Code | `/code-assist <command>` | `/code-assist report` |
| Cursor | `/code-assist <command>` | `/code-assist sync` |
| Antigravity | `/code-assist <command>`, or name the skill in your message | "use code-assist to show the report" |
| Codex | `$code-assist <command>` | `$code-assist init` |

The skill also triggers on plain requests such as "show my token report" or "sync the code map".

---

## Skill commands

### `init`

Sets up code-assist in the current project. Safe to run again at any time.

```
/code-assist init
```

- Runs the project installer (memory files, symbol index, hooks, `.gitignore`).
- **Existing project:** builds `.ai/CODEMAP.md` and `.ai/PATTERNS.md` once, cheaply. It reads only the
  symbol index, manifests (`package.json`, `pubspec.yaml`, …) and two or three sample files.
- **New project:** leaves the templates to fill up as you work.
- Asks before slimming an existing long `CLAUDE.md`.

Afterwards, start a new chat so the hooks load.

### `sync`

Refreshes the project memory. Run it after big refactors, after `git pull`, or once a week.

```
/code-assist sync
```

- Rebuilds `.ai/symbols.txt`.
- Updates `CODEMAP.md` for files added, removed or renamed since the last sync (uses `git diff`).
- Merges duplicate or contradicting lines in `LEARNINGS.md` and `PATTERNS.md` (newest wins).
- Moves personal habits (language, tone, style) from project learnings to your global preferences.
- Lists files over 600 lines as split candidates. It doesn't split them without asking.

### `report`

Shows tokens used and saved, optimizations, what was learned, and work done.

```
/code-assist report              # today, this project
/code-assist report --days 7     # last 7 days
/code-assist report --all        # all projects
```

See [Reading the report](#reading-the-report).

### `learn`

Teaches a rule by hand. Normally lessons are captured automatically when you correct the AI.

```
/code-assist learn "Use axios, never fetch"            # this project only
/code-assist learn --global "Reply in short sentences"  # every project
```

### `status`

Checks the setup: whether `.ai/` exists, the size of each memory file, the symbol count, and
whether hooks and `AGENTS.md` are in place.

```
/code-assist status
```

---

## Terminal scripts

In the commands below, `$CA` is `~/.claude/skills/code-assist` and `python3` may be `python` or
`py -3` on Windows.

### Install into a project

```bash
bash $CA/install.sh [project_dir] [--no-agents]
```

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\install.ps1" [-Project C:\path] [-NoAgents]
```

| Option | Effect |
|---|---|
| `project_dir` / `-Project` | Folder to set up (default: current folder) |
| `--no-agents` / `-NoAgents` | Don't create or modify `AGENTS.md` |

### Install or update the skill (per computer)

```bash
bash $CA/setup.sh [--force]
```

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\setup.ps1" [--force]
```

`--force` connects Cursor, Codex and Antigravity even if their config folders don't exist yet.

### Report

```bash
python3 $CA/scripts/report.py [--days N] [--all]
```

### Memory writer (`log.py`)

One command instead of editing files by hand. The AI uses this automatically; you can use it too.

| Command | Writes to |
|---|---|
| `python3 $CA/scripts/log.py learn "<lesson>"` | `.ai/LEARNINGS.md` |
| `python3 $CA/scripts/log.py learn --global "<lesson>"` | `~/.claude/code-assist/USER_PATTERNS.md` |
| `python3 $CA/scripts/log.py pattern "<convention>"` | `.ai/PATTERNS.md` |
| `python3 $CA/scripts/log.py done "<what was finished>"` | `.ai/HISTORY.md` (dated) |
| `python3 $CA/scripts/log.py optimize "<what>" [tokens]` | The optimization log shown in the report |

Duplicate lessons are ignored.

### Symbol index (`symbols.py`)

```bash
python3 $CA/scripts/symbols.py <project>                   # rebuild the whole index
python3 $CA/scripts/symbols.py <project> <file>            # re-index one file
python3 $CA/scripts/symbols.py <project> --outline <file>  # list a file's symbols with line numbers
```

Look up a symbol:

```bash
grep -n "calcTotal" .ai/symbols.txt
# calcTotal	fn	src/lib/pricing.ts:2
```

---

## Reading the report

```text
# Token report — my-app, today

## Tokens used
- Sessions: 3   Turns: 41
- Input (new): 52.0k   Cache write: 180.0k   Cache read: 1.20M   Output: 18.0k
- Total processed: 1.45M
- Cache hit rate: 84%

## Tokens saved (estimates)
- Smart reads: 36.0k  (22 partial reads, 3 blocked junk/vendor reads)
- Prompt cache discount: ~1.08M token-equivalents
- Lifetime smart-read savings: 410.0k   Lifetime tokens processed: 9.80M

## Optimizations (5)
- auto memory update: CODEMAP +2 files, PROGRESS/HISTORY  ×3
- context hit 95k -> saved progress & suggested /clear

## Learned (2)
- Use axios, not fetch
- Reply in short sentences (global)

## Work done (4 tasks, 11 files edited)
- Added discount logic to checkout
```

| Line | Meaning |
|---|---|
| **Input (new)** | Tokens sent that weren't cached: your messages, file contents, tool output. |
| **Cache write / Cache read** | Conversation and memory the model reused from cache. Cache reads cost about 10% of normal input. |
| **Cache hit rate** | Higher is better. A low rate usually means very short chats or frequently changing instructions. |
| **Smart reads** | Estimated tokens not spent because a file was read in part instead of whole (file size minus what was read, ÷4). |
| **Blocked junk/vendor reads** | Attempts to read `node_modules`, lock files or generated code that were stopped. |
| **Prompt cache discount** | Estimated saving from cache reads (90% of cache-read tokens). |
| **Optimizations** | Automatic actions: memory updates, context warnings, installs, syncs. |
| **Learned** | Lessons captured from your corrections. |

Token **usage** comes from the tool's own session data (available for Claude Code and Codex).
**Savings** are estimates and are recorded for every tool.

---

Next: [How it works](how-it-works.md) · [Configuration](configuration.md)
