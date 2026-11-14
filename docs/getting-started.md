# Getting started

This guide takes you from nothing to a project where your AI assistant remembers its work and uses
fewer tokens. It takes about five minutes.

- [1. Requirements](#1-requirements)
- [2. Install the skill on your computer](#2-install-the-skill-on-your-computer)
- [3. Set up a project](#3-set-up-a-project)
- [4. Daily workflow](#4-daily-workflow)
- [5. Using the same project on another computer](#5-using-the-same-project-on-another-computer)
- [6. Updating](#6-updating)
- [7. Uninstalling](#7-uninstalling)

---

## 1. Requirements

| Requirement | Check with | Get it |
|---|---|---|
| Git | `git --version` | https://git-scm.com |
| Python 3.8 or newer | `python3 --version` (Windows: `python --version` or `py -3 --version`) | https://www.python.org/downloads/ (Windows: tick **Add Python to PATH**) |
| At least one AI tool | — | Claude Code, Cursor, OpenAI Codex or Google Antigravity |

There are no other dependencies. code-assist uses only the Python standard library.

## 2. Install the skill on your computer

You do this **once per computer**. It installs code-assist into `~/.claude/skills/code-assist` and
connects every supported AI tool it finds.

**macOS, Linux, or Windows Git Bash**

```bash
git clone https://github.com/arifbiswas/code-assist.git ~/.claude/skills/code-assist
bash ~/.claude/skills/code-assist/setup.sh
```

**Windows PowerShell**

```powershell
git clone https://github.com/arifbiswas/code-assist.git "$HOME\.claude\skills\code-assist"
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\setup.ps1"
```

Expected output (tools you don't have are listed as "not found" and skipped):

```text
✅ code-assist skill ready at /Users/you/.claude/skills/code-assist  (Claude Code)
Other AI tools:
  Codex:       skill linked
               hooks -> /Users/you/.codex/hooks.json  (approve them once in Codex: /hooks)
  Antigravity: skill linked
               hooks -> /Users/you/.gemini/config/hooks.json
  Cursor:      hooks -> /Users/you/.cursor/hooks.json  (skill: Cursor reads ~/.claude/skills directly)
```

> Installed a new AI tool later? Run `setup.sh` / `setup.ps1` again and it will connect that tool too.

## 3. Set up a project

Open the project in your AI tool and ask:

| Tool | Type |
|---|---|
| Claude Code, Cursor, Antigravity | `/code-assist init` |
| Codex | `$code-assist init` |

Or, from a terminal:

```bash
bash ~/.claude/skills/code-assist/install.sh /path/to/your/project
```

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\install.ps1" -Project C:\path\to\project
```

### What happens

1. A `.ai/` folder is created with the project's memory files (see [How it works](how-it-works.md)).
2. Every function, class and API route is indexed into `.ai/symbols.txt`.
3. `CLAUDE.md` and `AGENTS.md` get a short block that tells AI tools to use the memory. Your
   existing content in those files is kept.
4. Claude Code hooks are added to `.claude/settings.local.json`, and read-blocking rules for
   `node_modules`, build output and lock files are added to `.claude/settings.json`.
5. Per-PC files are added to `.gitignore`.

### Existing project vs. new project

- **Existing project** (the installer prints `EXISTING project`): when you run `/code-assist init`
  through the AI, it builds `CODEMAP.md` (feature → file → functions) and `PATTERNS.md` (stack,
  commands, conventions) once. It reads only manifests, the symbol index and two or three sample
  files, not the whole codebase.
- **New project**: nothing else to do. The memory files fill up as you build.

### Then start a new chat

Hooks load when a session starts. **Open a new chat/session in the project** after setup.
In Codex, run `/hooks` once and approve the code-assist hooks.

## 4. Daily workflow

You don't need to change how you work. Just keep these habits:

1. **Name the place when you can.** "In the booking page, `calcTotal` gives the wrong total" is
   cheaper than "the total is wrong somewhere".
2. **Start a fresh chat for each new task** (`/clear` in Claude Code). Memory reloads
   automatically, so you lose nothing and stop paying for old conversation.
3. **When the AI says "Progress saved — start a fresh chat"**, do it. Context has grown large and
   every message is getting expensive.
4. **Correct it once.** When you say "don't do it this way" or "always use X", the lesson is saved
   and reloaded in every future session.
5. **Check your savings**: `/code-assist report` (Codex: `$code-assist report`).
6. **After a big change or `git pull`**: `/code-assist sync` refreshes the map.

## 5. Using the same project on another computer

What to commit:

| Commit ✅ | Don't commit (per PC, already in `.gitignore`) |
|---|---|
| `.ai/CODEMAP.md`, `PATTERNS.md`, `PROGRESS.md`, `LEARNINGS.md`, `HISTORY.md` | `.ai/symbols.txt` |
| `CLAUDE.md`, `AGENTS.md` | `.ai/RULES.md` |
| `.claude/settings.json` | `.claude/settings.local.json` |

On the other computer:

1. Install the skill there ([step 2](#2-install-the-skill-on-your-computer)).
2. Clone or pull the project.
3. Run `/code-assist init` (or `install.sh`) in the project. This recreates the per-PC files with
   that computer's paths and **never overwrites your notes**.

## 6. Updating

Run the setup script again. It pulls the latest version and refreshes tool connections:

```bash
bash ~/.claude/skills/code-assist/setup.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\code-assist\setup.ps1"
```

Projects keep working after an update. To pick up template or rule changes in a project, run
`install.sh` / `/code-assist init` in that project again.

## 7. Uninstalling

**From one project:**

1. In `.claude/settings.local.json`, delete the hook entries whose command contains `code-assist`.
2. In `CLAUDE.md` and `AGENTS.md`, delete the block between `<!-- code-assist:start -->` and
   `<!-- code-assist:end -->`.
3. Optionally delete `.ai/` (it contains your project notes, so keep a copy if you want them).

**From the computer:**

1. Remove the code-assist entries from `~/.cursor/hooks.json` and `~/.codex/hooks.json`, and the
   `"code-assist"` key from `~/.gemini/config/hooks.json`.
2. Delete the links `~/.agents/skills/code-assist` and `~/.gemini/config/skills/code-assist`.
3. Delete `~/.claude/skills/code-assist`. Your stats and preferences are in `~/.claude/code-assist/`;
   delete that folder too if you don't need them.

---

Next: [Commands](commands.md) · [How it works](how-it-works.md) · [AI tools](tools.md)
