# AI working rules (token-saver) — follow automatically, never wait to be asked

## Scope
- Change ONLY what the user asked. No unrequested refactors, renames, reformatting or "improvements".
  If you see something worth improving, mention it in one line at the end — don't apply it.
- Follow .ai/PATTERNS.md and the learnings loaded at session start. Match existing code style.

## Finding code (cheapest first)
1. .ai/CODEMAP.md (feature -> file -> symbol). Read it once per session, only when locating code.
2. `grep -n "<name>" .ai/symbols.txt` -> exact file:line.
3. Read with offset/limit (~±40 lines). Never read a big file whole "to understand".
4. Unknown location -> Grep/rg by keyword. Broad exploration -> Explore subagent (keeps your context small).
5. Never read node_modules, build output, lock files, or generated code.

## Output
- Short answers: what changed (file:line) + anything the user must do. No tutorials, no restating the code.
- Edit in place; never re-print whole files.
- Long command output: pipe through `| tail -40`; for tests show only failures.

## Memory (automatic)
- New / renamed / deleted file or new feature -> update .ai/CODEMAP.md (1 line each).
- After finishing a chunk of work -> overwrite .ai/PROGRESS.md (<=12 lines) and run
  `{{LOG}} done "<one line>"`.
- User corrects you or states a preference -> `{{LOG}} learn "<lesson>"`
  (add `--global` if it applies to every project, e.g. language, tone, style habits).
- You notice a repeated code convention -> `{{LOG}} pattern "<convention>"`.
- You make a token optimization (split a huge file, trimmed docs, merged duplicates) ->
  `{{LOG}} optimize "<what>"`.
- Keep every .ai file short: merge duplicates, delete stale lines. CODEMAP <= 150 lines.

## Context
- When told the context is large: save progress, then tell the user to type /clear
  (PROGRESS + learnings reload automatically, so nothing is lost).
