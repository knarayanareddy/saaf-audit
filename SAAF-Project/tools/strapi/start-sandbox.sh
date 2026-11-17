#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '%s\n' "Missing required command: $1" >&2
    exit 1
  fi
}

require_command docker
require_command python3

if [ ! -f "$ENV_FILE" ]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  printf '%s\n' "Created tools/strapi/.env from .env.example"
fi

python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
lines = env_path.read_text(encoding="utf-8").splitlines()
updated = []

for line in lines:
    if line.startswith("STRAPI_ADMIN_EMAIL="):
        updated.append("SAAF_" + line)
    elif line.startswith("STRAPI_ADMIN_PASSWORD="):
        updated.append("SAAF_" + line)
    else:
        updated.append(line)

env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
PY

printf '%s\n' "Starting Strapi container..."
docker compose -f "$COMPOSE_FILE" up -d --build strapi

printf '%s\n' "Waiting for Strapi health endpoint..."
if ! python3 - "$SCRIPT_DIR" <<'PY'
import json
import subprocess
import sys
import time
from pathlib import Path

script_dir = Path(sys.argv[1])
compose_file = script_dir / "docker-compose.yml"
deadline = time.time() + 180

def current_status() -> str:
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "ps", "--format", "json", "strapi"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    line = result.stdout.strip().splitlines()[-1]
    payload = json.loads(line)
    health = payload.get("Health")
    state = payload.get("State", "")
    if health:
        return health
    return state

while time.time() < deadline:
    status = current_status().lower()
    if status == "healthy":
      sys.exit(0)
    if status == "unhealthy":
      print("Strapi reported an unhealthy status.", file=sys.stderr)
      sys.exit(1)
    time.sleep(3)

print("Timed out waiting for Strapi to become healthy.", file=sys.stderr)
sys.exit(1)
PY
then
  printf '%s\n' "Startup failed. Inspect logs with:" >&2
  printf '%s\n' "  docker compose -f tools/strapi/docker-compose.yml logs strapi" >&2
  exit 1
fi

printf '%s\n' "Resetting and seeding the sandbox..."
if ! docker compose -f "$COMPOSE_FILE" run --rm seed; then
  printf '%s\n' "Seeding failed. Inspect logs with:" >&2
  printf '%s\n' "  docker compose -f tools/strapi/docker-compose.yml logs strapi" >&2
  exit 1
fi

cat <<'EOF'
Seeded Strapi sandbox is ready.
API:   http://localhost:1340/api
Admin: http://localhost:1340/admin
Creds: tools/strapi/.env (SAAF_STRAPI_ADMIN_EMAIL / SAAF_STRAPI_ADMIN_PASSWORD)

Rerunning ./tools/strapi/start-sandbox.sh resets the sandbox back to the committed seed data.
Stop the sandbox with:
  docker compose -f tools/strapi/docker-compose.yml down
EOF
