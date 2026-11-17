"""Build a platform-specific MCPB with an explicit source allowlist and locked wheels."""

import json
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_files(root: Path) -> list[Path]:
    """Only Python source is shipped; secrets must never be hardcoded in it."""
    return sorted(
        path for path in (root / "src" / "usecase_mcp").rglob("*.py")
        if not path.is_symlink() and "__pycache__" not in path.parts
    )


def build_bundle(root: Path = ROOT) -> Path:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required. See docs/preparation.md.")
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mcp-bundle-") as temporary:
        stage = Path(temporary) / "bundle"
        stage.mkdir()
        manifest = json.loads((root / "packaging" / "manifest.json").read_text())
        major, minor = sys.version_info[:2]
        manifest["compatibility"] = {
            "platforms": [sys.platform],
            "runtimes": {"python": f">={major}.{minor}.0 <{major}.{minor + 1}.0"},
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (stage / "BUILD-INFO.json").write_text(json.dumps({
            "python": [major, minor], "platform": sys.platform,
            "machine": platform.machine(), "sdk": "2.2.0",
            "note": "Python is not bundled. Use a matching interpreter and architecture.",
        }, indent=2) + "\n")
        shutil.copy2(root / "packaging" / "server.py", stage / "server.py")
        shutil.copy2(root / "LICENSE", stage / "LICENSE")
        for source in source_files(root):
            destination = stage / source.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        requirements = Path(temporary) / "requirements.txt"
        subprocess.run([
            uv, "export", "--locked", "--no-dev", "--no-emit-project",
            "--format", "requirements-txt", "--output-file", str(requirements),
        ], cwd=root, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([
            uv, "pip", "install", "--python", sys.executable,
            "--target", str(stage / "lib"), "--require-hashes",
            "--only-binary", ":all:", "-r", str(requirements),
        ], cwd=root, check=True)
        # Native dependencies make this archive specific to the build environment.
        output = dist / (
            f"{manifest['name']}-{manifest['version']}-{sys.platform}-"
            f"{platform.machine()}-py{major}{minor}.mcpb"
        )
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
                    archive.write(path, path.relative_to(stage))
        return output


def main() -> None:
    try:
        print(build_bundle())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Bundle build failed: {error}") from error


if __name__ == "__main__":
    main()
