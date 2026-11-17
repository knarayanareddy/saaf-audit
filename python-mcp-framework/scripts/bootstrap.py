"""Check prerequisites and clone/verify the pinned SDK. Uses only stdlib."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def ensure_reference(root: Path = ROOT) -> str:
    spec = json.loads((root / "reference.json").read_text())
    target = root / ".references" / "python-sdk"
    if target.is_symlink():
        raise RuntimeError("Reference path is a symlink; use a regular local clone.")
    if target.exists():
        if not (target / ".git").exists():
            raise RuntimeError(f"{target} exists but is not a Git clone. Move it aside manually.")
        origin = run("git", "remote", "get-url", "origin", cwd=target).removesuffix(".git")
        if origin != spec["url"]:
            raise RuntimeError("Reference origin does not match reference.json; no changes made.")
        if run("git", "status", "--porcelain", cwd=target):
            raise RuntimeError("Reference has local changes; preserve them before continuing.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--depth", "1", "--branch", spec["tag"], spec["url"], str(target))
    revision = run("git", "rev-parse", "HEAD", cwd=target)
    if revision != spec["commit"]:
        raise RuntimeError(
            "Reference revision differs from the pin. Move the clone aside and rerun; "
            "this script will not overwrite your checkout."
        )
    for example in spec["examples"]:
        if not (target / example).is_file():
            raise RuntimeError(f"Missing reference example: {example}")
    return revision


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11+ is required. Install it and rerun this script.", file=sys.stderr)
        return 1
    missing = [command for command in ("git", "uv") if not shutil.which(command)]
    if missing:
        print(f"Missing: {', '.join(missing)}. See docs/preparation.md.", file=sys.stderr)
        return 1
    try:
        revision = ensure_reference()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Preparation blocked: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        return 1
    print(f"SDK reference verified: {revision}")
    print("Next: uv sync --locked, then open your coding agent and follow AGENTS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
