# AI tools

code-assist has one memory format and one hook script. A small adapter translates each tool's hook
events into it.

| | Claude Code | Cursor | OpenAI Codex | Google Antigravity | Copilot, Gemini CLI, others |
|---|---|---|---|---|---|
| Reads `.ai/` memory | ✅ via `CLAUDE.md` | ✅ via `AGENTS.md` | ✅ via `AGENTS.md` | ✅ via `AGENTS.md` | ✅ via `AGENTS.md` (where supported) |
| Skill | `/code-assist` | `/code-assist` | `$code-assist` | `/code-assist` | – |
| Hooks installed | per project | global | global | global | – |
| Blocks big / vendor reads | ✅ | ✅ | ✅ (shell reads) | ✅ | – |
| Auto-updates memory | ✅ | ✅ | ✅ | ✅ | AI follows the rules itself |
| Learns from corrections | ✅ | ✅ (delivered at end of turn) | ✅ | ✅ | AI follows the rules itself |
| Token usage in report | ✅ | savings only | ✅ | savings only | – |

> **Testing status:** Claude Code support is the reference implementation. The Cursor, Codex and
> Antigravity adapters follow each tool's official hook documentation. They're tested by simulating
> each tool's hook input, but haven't been verified inside the apps yet. Please
> [open an issue](https://github.com/arifbiswas/code-assist/issues) if something doesn't behave as described.

---

## Claude Code

| | |
|---|---|
| Skill location | `~/.claude/skills/code-assist` |
| Hooks | `<project>/.claude/settings.local.json`, written by `install` |
| Events used | `SessionStart`, `UserPromptSubmit`, `PreToolUse` (Read), `PostToolUse` (Read, Edit, Write, MultiEdit, NotebookEdit), `Stop`, `SessionEnd` |

Setup: install the skill, then run `/code-assist init` in each project and start a new session.
Hooks are per project, so other folders aren't affected.

## Cursor

| | |
|---|---|
| Skill location | none needed: Cursor loads skills from `~/.claude/skills` |
| Hooks | `~/.cursor/hooks.json`, written by `setup` |
| Events used | `sessionStart`, `beforeSubmitPrompt`, `preToolUse` (Read), `beforeShellExecution` (matcher: whole-file read commands), `postToolUse` (Read), `afterShellExecution` (matcher: `sed`, `head`), `afterFileEdit`, `stop`, `sessionEnd` |

Notes:

- Cursor blocks an action when a permission hook returns no JSON or invalid JSON. code-assist
  always answers with `{"permission": "allow"}` unless it means to deny, including after an internal error.
- Cursor's `beforeSubmitPrompt` can't add context, so the "save this lesson" and "context is
  large" notes are delivered through the `stop` follow-up when the agent finishes its turn
  (`loop_limit: 1`, so this happens at most once).
- If Cursor's **Include third-party … configs** setting is on, Cursor also runs the Claude Code
  hooks from `.claude/settings.local.json`. code-assist detects this and skips the Claude copy, so
  nothing runs twice.

## OpenAI Codex

| | |
|---|---|
| Skill location | link `~/.agents/skills/code-assist` → `~/.claude/skills/code-assist` |
| Hooks | `~/.codex/hooks.json`, written by `setup` |
| Events used | `SessionStart`, `UserPromptSubmit`, `PreToolUse` (Bash), `PostToolUse` (Bash, apply_patch), `Stop`, `SessionEnd` |

Notes:

- **Approve the hooks once:** Codex reviews new hooks before running them. Open Codex and run
  `/hooks`, then approve the code-assist entries.
- Codex reads files through shell commands, so code-assist checks commands such as `cat` and
  `nl -ba` and suggests `sed -n 'A,Bp'` ranges instead.
- Edits made with `apply_patch` (added, updated, moved and deleted files) update the symbol index and CODEMAP queue.
- Token usage is read from Codex's session rollout (`token_count` events).

## Google Antigravity

| | |
|---|---|
| Skill location | link `~/.gemini/config/skills/code-assist` → `~/.claude/skills/code-assist` |
| Hooks | `~/.gemini/config/hooks.json` (key `"code-assist"`), written by `setup` |
| Events used | `SessionStart`, `PreInvocation`, `PreToolUse` (view_file, run_command), `PostToolUse` (view_file, run_command, write_to_file, replace_file_content, multi_replace_file_content), `Stop` |

Notes:

- Antigravity reads `AGENTS.md` as an always-on rule file, so the memory instructions apply to every chat.
- `PreInvocation` runs before every model call. code-assist acts only once per new user message.
- Context is injected with `injectSteps` / `systemMessage`. Antigravity's documentation shows two
  slightly different shapes for this field. If session memory doesn't appear at chat start,
  please report it.
- Antigravity's transcript format isn't documented, so the report shows savings but not token usage.

## Other tools (Copilot, Gemini CLI, Windsurf, Zed, …)

Any tool that reads `AGENTS.md` gets the memory instructions: read PROGRESS and LEARNINGS first,
locate code through CODEMAP and the symbol index, update PROGRESS after work. There are no hooks,
so nothing is enforced automatically and the AI follows the rules on its own.

To set up a project for these tools without Claude Code, use the terminal installer:

```bash
bash ~/.claude/skills/code-assist/install.sh /path/to/project
```

---

Next: [Configuration](configuration.md) · [Troubleshooting](troubleshooting.md)
