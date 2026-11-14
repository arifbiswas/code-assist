# Troubleshooting & FAQ

- [Something isn't working](#something-isnt-working)
- [Frequently asked questions](#frequently-asked-questions)

First step for any problem: run `/code-assist status` and check `~/.claude/code-assist/errors.log`.

---

## Something isn't working

### The hooks don't seem to run

1. **Start a new chat/session.** Hooks load at session start, so a chat that was already open
   won't pick them up.
2. **The project needs a `.ai/` folder.** Hooks do nothing elsewhere. Run `/code-assist init`.
3. **Codex:** run `/hooks` and approve the code-assist hooks. Codex skips unapproved hooks.
4. **Check the config:**
   - Claude Code: `.claude/settings.local.json` in the project contains `code-assist`.
   - Cursor: `~/.cursor/hooks.json`. Codex: `~/.codex/hooks.json`. Antigravity: `~/.gemini/config/hooks.json`.
   - If a file is missing, run `setup.sh` again. A tool that wasn't installed when setup ran is skipped.
5. **Test a hook by hand** (it should print a JSON line):

   ```bash
   cd /path/to/project
   echo '{"session_id":"t","cwd":"'"$PWD"'","source":"startup"}' | python3 ~/.claude/skills/code-assist/scripts/hooks.py session_start
   ```

### `Python 3.8+ is required`

Install Python from https://www.python.org/downloads/. On Windows, tick **Add Python to PATH**,
open a new terminal, and run setup again. If Windows opens the Microsoft Store when you type
`python`, turn off the "App execution aliases" for Python in Windows Settings.

### PowerShell says running scripts is disabled

Use the commands exactly as documented. They run the script with
`powershell -ExecutionPolicy Bypass -File …`, which affects only that one run.

### `setup.sh` fails with "Your local changes … would be overwritten"

This happens with an older version whose setup changed file permissions. Fix it once:

```bash
git -C ~/.claude/skills/code-assist checkout -- .
git -C ~/.claude/skills/code-assist config core.fileMode false
bash ~/.claude/skills/code-assist/setup.sh
```

### The AI refuses to read a file I need in full

That's the big-file guard. The AI was given the file's symbol list and can request the full range
explicitly (for example `Read` with a `limit` equal to the file length). Tell it "read the whole
file". To raise the limit, set `CODE_ASSIST_BIG_FILE_LINES` (see [Configuration](configuration.md)).

### A function is missing from `symbols.txt`

The indexer is pattern-based and can miss unusual syntax. Search with `grep -rn "name" src/`
instead. Rebuild the index with `/code-assist sync` or:

```bash
python3 ~/.claude/skills/code-assist/scripts/symbols.py .
```

### The report shows 0 tokens used

Usage is recorded when a session ends or the AI finishes a turn, and only for Claude Code and
Codex (Cursor and Antigravity show savings only). Run the report from inside the project, or use
`--all` to see every project.

### Session memory doesn't appear in Antigravity

Antigravity's documentation shows two shapes for the context field, and code-assist uses one of
them. Please [open an issue](https://github.com/arifbiswas/code-assist/issues) and include
`~/.claude/code-assist/errors.log` if it has any entries.

### Big-file reads aren't blocked in Cursor

Cursor doesn't document the argument names of its Read tool. code-assist accepts `file_path`,
`path` and `target_file`, plus `offset`/`limit` or `start_line_one_indexed`/`end_line_one_indexed_inclusive`.
If your Cursor version uses other names, please open an issue.

---

## Frequently asked questions

**Does the AI really "remember" now?**
No model remembers between sessions. code-assist stores memory in small files and loads the right
ones automatically at session start, which has the same effect at a fraction of the token cost.

**Can it type `/clear` for me?**
No. No hook can start a new chat. When the conversation gets large, the AI saves progress and asks
you to start a fresh chat. Because memory reloads automatically, nothing is lost.

**Will it change my existing `CLAUDE.md` or `AGENTS.md`?**
It only adds or refreshes a block between `<!-- code-assist:start -->` and `<!-- code-assist:end -->`.
Everything else in those files stays as you wrote it.

**Should I commit the `.ai/` folder?**
Yes, except `symbols.txt` and `RULES.md`, which are per-PC and already in `.gitignore`. Committing
the notes lets your other computers and your teammates start with the same project memory. See
[Getting started § 5](getting-started.md#5-using-the-same-project-on-another-computer).

**Does it send my code anywhere?**
No. Everything runs locally with the Python standard library. There are no network calls and no telemetry.

**How accurate are the "tokens saved" numbers?**
They're estimates: file size minus the part actually read, divided by four characters per token.
"Tokens used" comes from the tool's own usage records.

**Is it safe if a hook crashes?**
Yes. Hook errors are written to `errors.log` and the action continues. For tools that require an
answer (Cursor, Antigravity), code-assist always replies "allow" unless it deliberately denies.

**I used the older `token-saver` version.**
Run the install commands in [Getting started](getting-started.md#2-install-the-skill-on-your-computer).
Setup moves the old skill to `~/.claude/code-assist/backup/` and migrates your data. Then run
`/code-assist init` in each project.
