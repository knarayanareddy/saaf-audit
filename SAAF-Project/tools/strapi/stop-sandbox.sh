#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' "Missing required command: docker" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" down

printf '%s\n' "Strapi sandbox stopped."
