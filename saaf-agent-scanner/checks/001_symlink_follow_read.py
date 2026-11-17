"""SAAF-001: files from an untrusted tree (cloned repo / extracted archive / upload dir) are read without a symlink
or containment check.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, functions, snippet

CHECK = {
    "id": "SAAF-001",
    "slug": "symlink-follow-file-read",
    "category": "path-traversal",
    "severity": "High",
    "title": "Files from an untrusted repository or archive are read without a symlink/containment check",
    "intended": "Only files that physically live inside the cloned repository or extracted archive are read and returned.",
    "actual": "The code walks the untrusted tree (rglob/os.walk/glob) and calls read_text()/open() on each entry without "
              "is_symlink() or a resolve()-inside-root check; git and zip/tar preserve symlinks.",
    "impact": "A committed symlink such as notes.md -> /proc/self/environ or -> ~/.ssh/id_rsa makes the tool read and "
              "return server files and the process environment (API keys) to whoever supplied the repository.",
    "recommendation": "Skip entries where path.is_symlink() is true and reject any path whose resolve() is not inside the "
                      "resolved root; clone with `git -c core.symlinks=false`; use os.walk(followlinks=False); for "
                      "archives, reject symlink members before extracting.",
    "refs": "CWE-59, CWE-22, OWASP LLM06",
}

UNTRUSTED_SRC = re.compile(r"[\"']clone[\"']|git\s+clone|Repo\.clone_from|zipfile\.ZipFile|tarfile\.open|extractall|"
                           r"unpack_archive", re.I)
WALK = re.compile(r"\.rglob\(|\.glob\(|os\.walk\(|glob\.glob\(|\.iterdir\(")
READ = re.compile(r"\.read_text\(|\.read_bytes\(|\bopen\(")
GUARD = re.compile(r"is_symlink|islink|followlinks\s*=\s*False|is_relative_to|commonpath|core\.symlinks\s*=\s*false|"
                   r"\.resolve\(\)\.relative_to", re.I)


def run(repo):
    hits = []
    for rel in repo.files({".py"}):
        lines = repo.lines(rel)
        if not UNTRUSTED_SRC.search(repo.read(rel)):
            continue
        for a, b, head in functions(lines):
            body = "\n".join(lines[a:b])
            if UNTRUSTED_SRC.search(body) and WALK.search(body) and READ.search(body) and not GUARD.search(body):
                ln = next(i for i in range(a, b) if WALK.search(lines[i]))
                hits.append(Hit(rel, ln + 1, snippet(lines[ln]),
                                f"{head[:60]} walks an untrusted tree and reads files without a symlink/containment guard"))
    return hits
