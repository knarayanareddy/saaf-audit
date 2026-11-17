#!/bin/bash
# Double-click to start the joiners-movers-leavers agent on a Mac.
# First run: creates a local Python environment and installs the packages (needs internet once).
# After that it starts offline. Close the Terminal window to stop.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:$PATH"

echo ""
echo "  Joiners-movers-leavers agent"
echo "  ----------------------------"

PY=""
for candidate in python3 /usr/bin/python3 /opt/homebrew/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    PY="$candidate"; break
  fi
done
if [ -z "$PY" ]; then
  echo "  Python 3.9 or newer was not found."
  echo "  macOS will offer to install the developer tools; accept, then double-click this file again."
  xcode-select --install 2>/dev/null
  read -r -p "  Press Enter to close." _; exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "  First start: preparing the environment (one to two minutes)..."
  "$PY" -m venv .venv || { echo "  Could not create the environment."; read -r -p "  Press Enter to close." _; exit 1; }
  .venv/bin/python -m pip install --quiet --upgrade pip >/dev/null 2>&1
  .venv/bin/python -m pip install --quiet -r requirements.txt || { echo "  Installing packages failed. Check the internet connection and try again."; read -r -p "  Press Enter to close." _; exit 1; }
fi

if command -v claude >/dev/null 2>&1; then
  if claude auth status 2>/dev/null | grep -q '"loggedIn": *true'; then
    echo "  Claude Code: ready (live findings)."
  else
    echo "  Claude Code: installed but not logged in. Run 'claude' once to log in."
    echo "  The demo still works and uses the prepared result."
  fi
else
  echo "  Claude Code: not found. The demo still works and uses the prepared result."
fi

exec .venv/bin/python run.py "$@"
