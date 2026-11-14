# How it works

- [The problem](#the-problem)
- [The idea](#the-idea)
- [Memory files](#memory-files)
- [The symbol index](#the-symbol-index)
- [Automatic hooks](#automatic-hooks)
- [Learning your preferences](#learning-your-preferences)
- [Where token savings come from](#where-token-savings-come-from)
- [Files and folders](#files-and-folders)

---

## The problem

An AI assistant doesn't remember anything between sessions. To fix a small bug it often:

1. Opens several files to find where the code lives, reading thousands of lines it doesn't need.
2. Re-learns your conventions, then "improves" things you never asked it to touch.
3. Drags the whole conversation along, so every new message re-sends everything said so far.

Each of these costs tokens, and the cost grows with the size of the project and the length of the chat.

## The idea

Behave like an experienced developer who keeps notes:

```text
you: "the total on the booking page is wrong"
        │
        ▼
.ai/CODEMAP.md      Booking total -> src/lib/pricing.ts -> calcTotal
        │
        ▼
.ai/symbols.txt     calcTotal  fn  src/lib/pricing.ts:42
        │
        ▼
read lines 20–80 of pricing.ts   (not all 900 lines)
```

Memory lives in plain files inside the project, so any AI tool can read it. Hooks enforce the cheap
path automatically, so you don't have to repeat instructions.

## Memory files

All in the project's `.ai/` folder. Each is kept deliberately short.

| File | What it holds | Updated by | Loaded |
|---|---|---|---|
| `CODEMAP.md` | Feature → file → main functions, one line each, ≤150 lines | AI (asked automatically when new files appear), `sync` | Read when locating code |
| `PATTERNS.md` | Stack, run/test/lint commands, folder layout, naming and code conventions | AI, `log.py pattern`, `init` | Every session (imported by `CLAUDE.md`) |
| `PROGRESS.md` | Where you left off: done / in progress / next / open issues, ≤12 lines, **overwritten** each time | AI (asked automatically every ~4 edits) | Every session start |
| `HISTORY.md` | Dated one-line changelog | `log.py done` | Last 5 lines at session start |
| `LEARNINGS.md` | Corrections and preferences for this project | `log.py learn` | Every session start |
| `RULES.md` | The working rules for the AI (generated from the skill, per PC) | Installer | Every session (imported by `CLAUDE.md`) |
| `symbols.txt` | Generated index: name → file:line | Automatically on every edit | Searched with `grep`, never loaded whole |

Global, in `~/.claude/code-assist/`:

| File | What it holds |
|---|---|
| `USER_PATTERNS.md` | Your preferences that apply to every project (language, tone, style). Loaded at every session start. |
| `events.jsonl` | Log of savings, optimizations, learnings and edits (used by the report). |
| `sessions/` | Token usage per session, per day. |
| `config.json` | The Python command chosen at install. |
| `errors.log` | Hook errors, if any. Hooks never interrupt your work. |

### Why no line numbers in CODEMAP?

Line numbers change every time code is edited, so a map that stores them goes stale. CODEMAP stores
**names**, and `symbols.txt` (rebuilt automatically) turns a name into the current line.

## The symbol index

`symbols.txt` has one line per symbol:

```text
BookingTable	fn	src/app/bookings/page.tsx:1
calcTotal	fn	src/lib/pricing.ts:42
PriceService	class	src/lib/pricing.ts:60
POST /bookings	route	src/server/routes/booking.ts:12
```

- Built by a dependency-free Python indexer. It understands JavaScript/TypeScript/React/Vue/Svelte,
  Python, Dart/Flutter, PHP/Laravel and Go, with generic rules for Java, Kotlin, Swift, Rust, C# and Ruby.
- Finds functions, arrow-function components, classes, types/interfaces/enums, methods, and API
  routes (Express, FastAPI/Flask, Laravel).
- Skips `node_modules`, build output, generated files, lock files and tests.
- A full rebuild runs at install and `sync`. After that, only the edited file is re-indexed.

## Automatic hooks

Hooks are small commands your AI tool runs at certain moments. code-assist's hooks do nothing in
folders without a `.ai/` directory.

| Moment | What code-assist does |
|---|---|
| **Session start** (also after `/clear` and auto-compaction) | Injects PROGRESS, the last HISTORY lines, LEARNINGS and your global preferences, so a fresh chat knows where you left off. |
| **Before a file read** | If the file is generated or vendor code, the read is blocked. If the file is over 300 lines and no range was requested, the read is blocked and the AI is given that file's symbol list with line numbers instead, so it reads only the part it needs. It can still read the whole file by explicitly asking for the full range. |
| **Before a shell command** (Codex, Cursor, Antigravity) | Same check for `cat`, `nl`, `bat`, `less`, `more`, `type`, `Get-Content`. |
| **After a read** | A partial read (`offset/limit`, `sed -n 'A,Bp'`, `head -n`) is logged as tokens saved. |
| **After an edit** | That file's symbols are re-indexed, and new source files are queued for CODEMAP. |
| **When you send a message** | If the conversation is over 80k tokens, the AI is told to save progress and suggest a fresh chat. If your message looks like a correction ("don't", "always", "never", "instead", …), the AI is reminded to save the lesson. |
| **When the AI finishes** | If new files aren't in CODEMAP, or there have been 4+ edits since PROGRESS was updated, the AI is asked to update them quietly before stopping. It's asked at most once per turn. |
| **Session end** | Token usage is recorded for the report. |

See [AI tools](tools.md) for exactly which events each tool supports.

## Learning your preferences

1. You say something like "don't use `any`, always write proper types".
2. The prompt hook notices correction words and reminds the AI to record it.
3. The AI runs `log.py learn "Always write proper TypeScript types; never use any"`. Duplicates are ignored.
4. Every future session starts with that lesson loaded.
5. `sync` merges similar lessons and moves personal habits to your global `USER_PATTERNS.md`, so
   they follow you to every project.

Recognized correction words include English ("don't", "never", "always", "instead", "wrong",
"prefer", "revert", "undo") and Bangla in Latin script and Bengali script ("vul", "eivabe na",
"sob somoy", "ভুল", "সবসময়", "এভাবে না", …).

## Where token savings come from

| Mechanism | Typical effect |
|---|---|
| Partial reads guided by the symbol index | Reading 60 lines of a 900-line file uses about 7% of the tokens. |
| Blocking vendor, lock and generated files | One lock file can be 50k+ tokens. |
| Fresh chats with automatic memory reload | Each message stops re-sending a long history. |
| Short, stable memory files | They stay in the prompt cache, where they're billed at roughly 10% of the normal input price. |
| "Change only what was asked" rule | No unrequested refactors to read, write and review. |
| Short answers rule | Output tokens are the most expensive ones. |

## Files and folders

```text
your-project/
├── CLAUDE.md                     + code-assist block (imports RULES and PATTERNS)
├── AGENTS.md                     + code-assist block (for Cursor, Codex, Antigravity, Copilot, …)
├── .claude/
│   ├── settings.json             + read-deny rules            (commit)
│   └── settings.local.json       + Claude Code hooks          (per PC, git-ignored)
└── .ai/
    ├── CODEMAP.md  PATTERNS.md  PROGRESS.md  HISTORY.md  LEARNINGS.md   (commit)
    ├── RULES.md                                                          (per PC, git-ignored)
    └── symbols.txt                                                       (generated, git-ignored)

~/.claude/skills/code-assist/     the skill (git clone)
~/.claude/code-assist/            your global preferences, stats and logs
~/.cursor/hooks.json              Cursor hooks         (added by setup)
~/.codex/hooks.json               Codex hooks          (added by setup)
~/.gemini/config/hooks.json       Antigravity hooks    (added by setup)
~/.agents/skills/code-assist      link for Codex
~/.gemini/config/skills/code-assist  link for Antigravity
```

---

Next: [AI tools](tools.md) · [Configuration](configuration.md)
