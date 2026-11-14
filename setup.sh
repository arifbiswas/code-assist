#!/usr/bin/env bash
# Finish install / update the code-assist skill (macOS / Linux / Windows Git Bash).
# First time:  git clone https://github.com/arifbiswas/code-assist.git ~/.claude/skills/code-assist
#              bash ~/.claude/skills/code-assist/setup.sh
# Update:      bash ~/.claude/skills/code-assist/setup.sh
set -euo pipefail
REPO="https://github.com/arifbiswas/code-assist.git"
SKILLS="$HOME/.claude/skills"
DEST="$SKILLS/code-assist"
BK_DIR="$HOME/.claude/code-assist/backup"

command -v git >/dev/null || { echo "git is required: https://git-scm.com"; exit 1; }
command -v python3 >/dev/null || command -v python >/dev/null || command -v py >/dev/null \
  || { echo "Python 3.8+ is required: https://www.python.org/downloads/"; exit 1; }

# old name (token-saver) -> backed up so Claude doesn't load two copies
if [ -e "$SKILLS/token-saver" ]; then
  mkdir -p "$BK_DIR" && mv "$SKILLS/token-saver" "$BK_DIR/token-saver-$(date +%Y%m%d%H%M%S)"
  echo "   old token-saver skill moved to $BK_DIR"
fi

if [ -d "$DEST/.git" ]; then
  echo "Updating code-assist..."
  git -C "$DEST" pull --ff-only --quiet
else
  if [ -e "$DEST" ]; then
    mkdir -p "$BK_DIR" && mv "$DEST" "$BK_DIR/code-assist-$(date +%Y%m%d%H%M%S)"
  fi
  mkdir -p "$SKILLS"
  git clone --depth 1 --quiet "$REPO" "$DEST"
fi
chmod +x "$DEST/install.sh" "$DEST"/scripts/*.py 2>/dev/null || true

PY=""
for c in python3 python "py -3"; do
  if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || { echo "Python 3.8+ is required: https://www.python.org/downloads/"; exit 1; }

echo "✅ code-assist skill ready at $DEST  (Claude Code)"
# Codex + Antigravity: link the skill and install their global hooks (skipped if not installed)
CODE_ASSIST_PY="$PY" $PY "$DEST/scripts/setup_agents.py" "$@"
echo
echo "Next, in any project:"
echo "  - Claude Code / Antigravity:  /code-assist init     - Codex:  \$code-assist init"
echo "  - or terminal:                bash ~/.claude/skills/code-assist/install.sh /path/to/project"
