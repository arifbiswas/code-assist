# Changelog

## 2026-11-14

### Documentation
- Full English documentation in `docs/`: getting started, commands, how it works, AI tools,
  configuration, troubleshooting.

### Changed
- Claude Code hooks now go in `.claude/settings.local.json` (per PC, git-ignored). Shared
  read-deny rules stay in `.claude/settings.json`. Older installs are migrated when you re-run `init`.
- `.ai/RULES.md` and `.claude/settings.local.json` are added to `.gitignore`, because they contain
  paths for one PC.
- Data from the old `token-saver` name is now merged correctly even if `~/.claude/code-assist`
  already exists.

### Added
- **Cursor** support: global hooks in `~/.cursor/hooks.json`.
- **OpenAI Codex** support: global hooks in `~/.codex/hooks.json`, skill link in `~/.agents/skills`.
- **Google Antigravity** support: global hooks in `~/.gemini/config/hooks.json`, skill link in
  `~/.gemini/config/skills`.
- Windows support: `setup.ps1` and `install.ps1`, UTF-8-safe hooks, and automatic detection of the
  Python command.
- `AGENTS.md` block so any agent that reads it shares the same memory.

### Renamed
- `token-saver` → `code-assist` (repository, skill, data folder, environment variables).

## Initial release
- Project memory files, symbol index, Claude Code hooks, preference learning, token report.
