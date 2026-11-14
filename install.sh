#!/usr/bin/env bash
# token-saver installer — safe to run again (idempotent, never overwrites your notes).
#   bash ~/.claude/skills/token-saver/install.sh [project_dir]
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$(cd "${1:-$PWD}" && pwd)"
LOG="python3 \"$SKILL_DIR/scripts/log.py\""

command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
mkdir -p "$PROJ/.ai" "$HOME/.claude/token-saver"

# 1) memory files (only created if missing; RULES.md is skill-owned and refreshed)
for f in CODEMAP PATTERNS PROGRESS LEARNINGS HISTORY; do
  [ -f "$PROJ/.ai/$f.md" ] || cp "$SKILL_DIR/templates/$f.md" "$PROJ/.ai/$f.md"
done
python3 - "$SKILL_DIR/templates/RULES.md" "$PROJ/.ai/RULES.md" "$LOG" <<'PY'
import sys; src, dst, log = sys.argv[1:4]
open(dst, "w").write(open(src).read().replace("{{LOG}}", log))
PY
[ -f "$HOME/.claude/token-saver/USER_PATTERNS.md" ] || \
  printf '# User preferences (all projects)\n' > "$HOME/.claude/token-saver/USER_PATTERNS.md"

# 2) CLAUDE.md: import rules + patterns (appends a block, keeps your content)
CM="$PROJ/CLAUDE.md"
if ! grep -q "token-saver:start" "$CM" 2>/dev/null; then
  [ -f "$CM" ] || printf '# %s\n' "$(basename "$PROJ")" > "$CM"
  printf '\n<!-- token-saver:start -->\n@.ai/RULES.md\n@.ai/PATTERNS.md\n<!-- token-saver:end -->\n' >> "$CM"
fi

# 3) hooks + deny rules -> .claude/settings.json (merged, existing settings kept)
python3 "$SKILL_DIR/scripts/merge_settings.py" "$PROJ/.claude/settings.json" "$SKILL_DIR"

# 4) generated index stays out of git
if [ -f "$PROJ/.gitignore" ] && ! grep -q "^.ai/symbols.txt" "$PROJ/.gitignore"; then
  printf '\n.ai/symbols.txt\n' >> "$PROJ/.gitignore"
fi

# 5) symbol index
RES="$(python3 "$SKILL_DIR/scripts/symbols.py" "$PROJ")"
FILES="$(echo "$RES" | awk '{print $2}')"

python3 -c "import sys; sys.path.insert(0, sys.argv[1]); from common import log_event; log_event(sys.argv[2], 'optimize', 'token-saver installed')" "$SKILL_DIR/scripts" "$PROJ"

echo "✅ token-saver installed in $PROJ"
echo "   $RES"
if [ "${FILES:-0}" -gt 5 ]; then
  echo "   EXISTING project detected -> in Claude run:  /token-saver init   (builds CODEMAP + PATTERNS once)"
else
  echo "   NEW project -> memory files will fill up automatically as you work."
fi
echo "   Start a NEW Claude session in this folder so the hooks load."
