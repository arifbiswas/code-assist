# Configuration

The defaults work for most projects. Everything below is optional.

- [Tuning thresholds](#tuning-thresholds)
- [Installer options](#installer-options)
- [Editing the memory files](#editing-the-memory-files)
- [Blocked paths](#blocked-paths)
- [Python command](#python-command)
- [Customizing the rules](#customizing-the-rules)

---

## Tuning thresholds

| Variable | Default | Meaning |
|---|---|---|
| `CODE_ASSIST_BIG_FILE_LINES` | `300` | Files longer than this can't be read whole without asking for the full range. |
| `CODE_ASSIST_CLEAR_AT` | `80000` | Conversation size (tokens) at which the AI saves progress and suggests a fresh chat. It's repeated every +30k. |
| `CODE_ASSIST_PROGRESS_EVERY` | `4` | Number of edits after which the AI is asked to update PROGRESS and HISTORY. |

**Claude Code:** add an `env` section to `.claude/settings.local.json` (this project) or
`~/.claude/settings.json` (all projects):

```json
{
  "env": {
    "CODE_ASSIST_BIG_FILE_LINES": "500",
    "CODE_ASSIST_CLEAR_AT": "120000"
  }
}
```

**Cursor, Codex, Antigravity:** set the variables in your shell profile (`~/.zshrc`, `~/.bashrc`,
or Windows environment variables) and restart the tool.

```bash
export CODE_ASSIST_BIG_FILE_LINES=500
```

## Installer options

| Option | Effect |
|---|---|
| `--no-agents` (`-NoAgents` in PowerShell) | Don't create or modify `AGENTS.md`. Use this if the project should only be set up for Claude Code. |
| `setup.sh --force` | Connect Cursor, Codex and Antigravity even if their config folders don't exist yet. |

The installer is idempotent. Running it again refreshes code-assist's own parts (rules, hooks,
index) and never overwrites `CODEMAP`, `PATTERNS`, `PROGRESS`, `LEARNINGS` or `HISTORY`.

## Editing the memory files

The `.ai/*.md` files are plain Markdown and you can edit them yourself. Some guidelines:

- **CODEMAP.md**: one line per entry, in the form `- <feature> -> <path> -> <main symbols>`. Group entries
  under `## Feature` headings. Don't add line numbers.
- **PATTERNS.md**: short bullets. Put the commands you run (`npm run dev`, `flutter test`, …) at the top.
- **LEARNINGS.md**: one rule per line. Delete anything that's no longer true.
- **PROGRESS.md**: overwritten after each chunk of work, so don't keep long-term notes here.

Shorter files mean fewer tokens on every session start. `/code-assist sync` compacts them for you.

## Blocked paths

Blocked by both the hooks and Claude Code's permission rules in `.claude/settings.json`:

- Folders: `node_modules`, `dist`, `build`, `.next`, `.nuxt`, `out`, `coverage`, `.dart_tool`,
  `Pods`, `vendor`, `.venv`, `venv`, `target`, `.gradle`, `.turbo`, `.cache`, `.expo`, `storage`,
  `bin`, `obj`, and others.
- Lock files: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `pubspec.lock`, `composer.lock`,
  `Podfile.lock`, `Cargo.lock`, `poetry.lock`, `Gemfile.lock`.
- Generated files: `*.min.js`, `*.min.css`, `*.map`, `*.g.dart`, `*.freezed.dart`.

To allow one of these in Claude Code, remove the matching `Read(...)` line from
`permissions.deny` in `.claude/settings.json`. The hook lists are in `scripts/common.py`
(`IGNORE_DIRS`, `LOCK_FILES`, `GENERATED_SUFFIXES`).

## Python command

`setup` and `install` detect a working Python 3.8+ (`python3`, then `python`, then `py -3`) and save
it in `~/.claude/code-assist/config.json`:

```json
{ "python": "python3" }
```

All hooks use this command. If you change your Python installation, run `setup` again.

## Customizing the rules

`.ai/RULES.md` is regenerated from `templates/RULES.md` on every install, so edits to the project
copy get replaced. To change the rules:

- **For one project:** add your rules to `CLAUDE.md` / `AGENTS.md` outside the code-assist block,
  or to `.ai/PATTERNS.md`.
- **For everyone:** edit `templates/RULES.md` in your fork of this repository.

---

Next: [Troubleshooting](troubleshooting.md)
