# code-assist

**Project memory for AI coding assistants: fewer tokens, better answers.**

code-assist gives your AI assistant a map of your project and a memory that survives between
chats. Instead of re-reading whole files every time, the AI looks up exactly where the code is and
reads only those lines. It remembers where you left off, learns your preferences, and shows you how
many tokens you used and saved.

Works with **Claude Code, Cursor, OpenAI Codex and Google Antigravity** (any tool that reads
`AGENTS.md` gets the memory too), on **macOS, Linux and Windows**.

```text
you: "the total on the booking page is wrong"

  .ai/CODEMAP.md    Booking total -> src/lib/pricing.ts -> calcTotal
  .ai/symbols.txt   calcTotal  fn  src/lib/pricing.ts:42
  read lines 20–80 of pricing.ts                      (not all 900 lines)
```

## Features

- **Code map and symbol index.** The AI finds `file:line` in one lookup instead of opening files to search.
- **Big-file guard.** Whole-file reads of large files are replaced by the file's outline, so only the needed range is read.
- **Junk blocker.** `node_modules`, lock files, build output and generated code are never read.
- **Memory across chats.** Progress, history and learnings reload automatically, so starting a fresh chat loses nothing.
- **Self-updating docs.** New files go into the map and progress is saved, without you asking.
- **Learns from corrections.** Say "don't do it that way" once and every future session knows.
- **Stays in scope.** Rules stop unrequested refactors and long explanations.
- **Token report.** Tokens used and saved, optimizations made, and what was learned, per day or per project.
- **Local only.** Python standard library, no network calls, no telemetry.

## Quick start

**1. Install (once per computer)**

```bash
# macOS / Linux / Windows Git Bash
git clone https://github.com/arifbiswas/code-assist.git ~/.claude/skills/code-assist
bash ~/.claude/skills/code-assist/setup.sh
```

```powershell
# Windows PowerShell
git clone https://github.com/arifbiswas/code-assist.git "$HOME\.claude\skills\code-assist"
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\setup.ps1"
```

Requires Git and Python 3.8+. Setup connects every supported AI tool it finds.

**2. Set up a project.** In your AI tool, inside the project:

```text
/code-assist init        Claude Code, Cursor, Antigravity
$code-assist init        Codex
```

**3. Start a new chat.** That's it: everything else is automatic.

**4. See your savings** any time with `/code-assist report`.

## Supported tools

| | Claude Code | Cursor | Codex | Antigravity | Others (Copilot, Gemini CLI, …) |
|---|---|---|---|---|---|
| Project memory | ✅ | ✅ | ✅ | ✅ | ✅ via `AGENTS.md` |
| Skill command | `/code-assist` | `/code-assist` | `$code-assist` | `/code-assist` | – |
| Automatic hooks | ✅ | ✅ | ✅ | ✅ | – |
| Token usage in report | ✅ | savings only | ✅ | savings only | – |

Cursor, Codex and Antigravity support follows each tool's official hook docs and has been tested
by simulating each tool's hook input, but not yet inside the apps. Details are in [AI tools](docs/tools.md).

## Documentation

| Guide | What's inside |
|---|---|
| [Getting started](docs/getting-started.md) | Install, first project, daily workflow, multiple computers, updating, uninstalling |
| [Commands](docs/commands.md) | Every skill command and script, and how to read the report |
| [How it works](docs/how-it-works.md) | Memory files, symbol index, hooks, learning, where savings come from |
| [AI tools](docs/tools.md) | Per-tool setup and behavior: Claude Code, Cursor, Codex, Antigravity, others |
| [Configuration](docs/configuration.md) | Thresholds, installer options, blocked paths, customizing rules |
| [Troubleshooting & FAQ](docs/troubleshooting.md) | Common problems and questions |
| [Changelog](CHANGELOG.md) | Version history |

## Commands at a glance

| Command | Does |
|---|---|
| `/code-assist init` | Set up the current project (builds the code map for existing code) |
| `/code-assist report [--days N] [--all]` | Tokens used and saved, optimizations, learnings |
| `/code-assist sync` | Refresh the map after big changes or `git pull`, and compact memory |
| `/code-assist learn "<rule>" [--global]` | Teach a rule by hand |
| `/code-assist status` | Check the setup |

Update code-assist any time by running `setup.sh` / `setup.ps1` again.

## What gets added to your project

```text
CLAUDE.md, AGENTS.md            + a short code-assist block (your content is kept)
.claude/settings.json           + read-deny rules for junk folders            (commit)
.claude/settings.local.json     + Claude Code hooks                           (per PC, git-ignored)
.ai/CODEMAP.md                  feature -> file -> symbols                     (commit)
.ai/PATTERNS.md                 stack, commands, conventions                   (commit)
.ai/PROGRESS.md                 where you left off                             (commit)
.ai/HISTORY.md                  dated changelog                                (commit)
.ai/LEARNINGS.md                your corrections for this project              (commit)
.ai/RULES.md, .ai/symbols.txt   generated per PC                               (git-ignored)
```

## Limits

- You start fresh chats yourself. No tool lets a hook do it, so the AI tells you when it's time.
- "Tokens saved" figures are estimates. "Tokens used" comes from each tool's own usage data.
- The symbol index is pattern-based and may miss unusual syntax.

## Contributing

Issues and pull requests are welcome, especially reports from real Cursor, Codex and Antigravity
use. Please include `~/.claude/code-assist/errors.log` (if present) and your OS and tool version.

## License

[MIT](LICENSE)
