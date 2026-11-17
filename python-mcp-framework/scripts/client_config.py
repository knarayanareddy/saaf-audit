"""Print concrete client configuration; never change the user's settings."""

import argparse
import json
import re
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client", choices=["codex", "claude"])
    parser.add_argument("--name", required=True, help="Use-case name, e.g. invoice-search")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", args.name):
        parser.error(
            "Name must use lowercase letters, digits and single hyphens; start with a letter."
        )
    root = Path(__file__).resolve().parents[1]
    python = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        parser.error("Project environment missing. Run uv sync --locked first.")
    # Keep the venv path: resolving its symlink would lose installed packages.
    config = {
        "command": str(python), "args": ["-m", "usecase_mcp"],
        "env": {"MCP_SERVER_NAME": args.name},
    }
    if args.client == "codex":
        print(f"[mcp_servers.{args.name}]")
        print(f"command = {json.dumps(config['command'])}")
        print(f"args = {json.dumps(config['args'])}")
        print(f"[mcp_servers.{args.name}.env]")
        print(f"MCP_SERVER_NAME = {json.dumps(args.name)}")
    else:
        print(json.dumps({"mcpServers": {args.name: config}}, indent=2))


if __name__ == "__main__":
    main()
