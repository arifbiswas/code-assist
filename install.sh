#!/usr/bin/env bash
# code-assist: install into a project (macOS / Linux / Windows Git Bash)
#   bash ~/.claude/skills/code-assist/install.sh [project_dir] [--no-agents]
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=""
for c in python3 python "py -3"; do
  if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || { echo "Python 3.8+ is required: https://www.python.org/downloads/"; exit 1; }
PROJ="${1:-$PWD}"; [ $# -gt 0 ] && shift
CODE_ASSIST_PY="$PY" $PY "$DIR/scripts/install.py" "$PROJ" "$@"
