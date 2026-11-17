"""Bundle entrypoint; paths are relative to this file, never the current folder."""

import json
import platform
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
build = json.loads((root / "BUILD-INFO.json").read_text())
if (
    list(sys.version_info[:2]) != build["python"]
    or sys.platform != build["platform"]
    or platform.machine().lower() != build["machine"].lower()
):
    raise SystemExit(
        "Bundle runtime mismatch. Select the Python/platform listed in BUILD-INFO.json."
    )
sys.path[:0] = [str(root / "src"), str(root / "lib")]

from usecase_mcp.server import main  # noqa: E402

main()
