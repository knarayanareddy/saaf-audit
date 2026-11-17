#!/bin/bash
HANDLE="$1"
[[ "$HANDLE" =~ ^[A-Za-z0-9-]+$ ]] || exit 1
gh api "/users/$HANDLE" --jq .id
eval "$(ssh-agent -s)"
eval "$(pyenv init -)"
bash -c 'echo "$0"' "$HANDLE"
