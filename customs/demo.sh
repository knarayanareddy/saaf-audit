#!/usr/bin/env bash
# Customs demo. Runs offline.
#
# Builds a throwaway git repository with a clean audit skill, then adds a
# contribution that hides instructions in that skill and adds a tool
# configuration. Customs clears the first and blocks the second.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CUSTOMS="$HERE/customs/customs.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' \
  || { echo "Customs needs Python 3.11 or later."; exit 2; }

pause() { if [ -t 0 ]; then read -r -p $'\nPress Enter to continue...' _; fi; echo; }

cd "$WORK"
git init -q
git checkout -q -b main
cp -R "$HERE/tests/fixtures/clean/." .
git add -A
git -c user.name="SAAF demo" -c user.email="demo@saafproject.com" commit -qm "Add vendor review skill"

echo "=== Step 1: the shared repository today, with a clean vendor review skill ==="
python3 "$CUSTOMS" || true
pause

git checkout -q -b contribution
cp -R "$HERE/tests/fixtures/poisoned/." .
git add -A
git -c user.name="Friendly contributor" -c user.email="demo@saafproject.com" commit -qm "Improve vendor review skill"

echo "=== Step 2: a pull request that 'improves' the skill ==="
git --no-pager diff --stat main...contribution
pause

echo "=== Step 3: Customs inspects the pull request ==="
set +e
python3 "$CUSTOMS" --changed-since main
status=$?
set -e
echo
echo "Customs exit code: $status (0 cleared, 1 blocked, 2 could not run)"
