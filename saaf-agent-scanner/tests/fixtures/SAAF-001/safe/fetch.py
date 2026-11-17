import subprocess, tempfile
from pathlib import Path

def fetch_repo(url):
    tmp = Path(tempfile.mkdtemp()).resolve()
    subprocess.run(["git", "-c", "core.symlinks=false", "clone", "--", url, str(tmp)])
    out = []
    for p in tmp.rglob("*.md"):
        if p.is_symlink() or not p.resolve().is_relative_to(tmp):
            continue
        out.append({"path": str(p), "content": p.read_text()})
    return out
