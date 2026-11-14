#!/usr/bin/env bash
# One-line install / update of the token-saver skill for Claude Code:
#   curl -fsSL https://raw.githubusercontent.com/arifbiswas/claude-token-saver/main/setup.sh | bash
set -euo pipefail
REPO="https://github.com/arifbiswas/claude-token-saver.git"
DEST="$HOME/.claude/skills/token-saver"

for c in git python3; do
  command -v "$c" >/dev/null || { echo "❌ $c is required"; exit 1; }
done

if [ -d "$DEST/.git" ]; then
  echo "↻ Updating token-saver…"
  git -C "$DEST" pull --ff-only --quiet
else
  if [ -e "$DEST" ]; then
    BK="$HOME/.claude/token-saver/backup-$(date +%Y%m%d%H%M%S)"
    mkdir -p "$(dirname "$BK")" && mv "$DEST" "$BK"
    echo "   (old copy moved to $BK)"
  fi
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 --quiet "$REPO" "$DEST"
fi
chmod +x "$DEST/install.sh" "$DEST"/scripts/*.py

# Projects that already use token-saver keep working: hooks point to $DEST.
echo "✅ token-saver skill ready at $DEST"
echo
echo "Next, in any project:"
echo "  • In Claude Code:  /token-saver init"
echo "  • or terminal:     bash ~/.claude/skills/token-saver/install.sh /path/to/project"
