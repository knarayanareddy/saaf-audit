import subprocess, tempfile
from pathlib import Path

def fetch_repo(url):
    tmp = tempfile.mkdtemp()
    subprocess.run(["git", "clone", "--depth", "1", url, tmp])
    return [{"path": str(p), "content": p.read_text()} for p in Path(tmp).rglob("*.md")]
