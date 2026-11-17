"""Where repository content comes from: the GitHub org (via `gh`) or a local directory.

GitHubSource hardens the `gh()` helper from scrape_hackathon_repos.py (copied, not imported:
that module creates directories and configures logging at import time). Every repo is pinned
to its HEAD commit; files are fetched as blobs by SHA, which sidesteps path encoding for
branch names with slashes and file names with spaces, and makes the cache content-addressed.
"""

import base64
import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


class GhError(RuntimeError):
    """A `gh` call failed."""


class GhNotFound(GhError):
    """HTTP 404."""


class GhEmptyRepo(GhError):
    """HTTP 409: the repository has no commits."""


class GhRateLimited(GhError):
    """HTTP 403/429 caused by rate limiting."""


@dataclass
class RepoInfo:
    name: str
    private: bool = True
    size: int = 1
    default_branch: str = "main"
    archived: bool = False
    head_sha: Optional[str] = None
    truncated: bool = False
    error: Optional[str] = None
    files: Dict[str, int] = field(default_factory=dict)  # path -> size in bytes


def encode_branch(branch: str) -> str:
    """URL-encode a branch name for use in an API path (slashes included)."""
    return quote(branch, safe="")


def _classify_gh_failure(stderr: str) -> GhError:
    text = stderr.lower()
    if "http 404" in text or "not found" in text:
        return GhNotFound(stderr.strip())
    if "http 409" in text or "git repository is empty" in text:
        return GhEmptyRepo(stderr.strip())
    if "rate limit" in text or "http 429" in text or ("http 403" in text and "limit" in text):
        return GhRateLimited(stderr.strip())
    return GhError(stderr.strip())


def gh(args: List[str], raw: bool = False, timeout: int = 60) -> Any:
    """Run `gh <args>`; return parsed JSON (or text when raw=True). Raises GhError subclasses."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        raise GhError("GitHub CLI `gh` not found. Install it and run `gh auth login`.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GhError(f"gh timed out after {timeout}s: {' '.join(cmd)}") from exc
    if result.returncode != 0:
        raise _classify_gh_failure(result.stderr or result.stdout)
    if raw:
        return result.stdout
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(f"Unparseable JSON from: {' '.join(cmd)}") from exc


class GitHubSource:
    """Reads repos from a GitHub org with a SHA-pinned, content-addressed local cache."""

    kind = "github"

    def __init__(self, org: str, cache_dir: Path, offline: bool = False, refresh: bool = False) -> None:
        self.org = org
        self.offline = offline
        self.refresh = refresh
        self.cache_dir = cache_dir
        self.repo_cache = cache_dir / "org" / org / "repos"
        self.blob_cache = cache_dir / "blobs"
        self.repo_cache.mkdir(parents=True, exist_ok=True)
        self.blob_cache.mkdir(parents=True, exist_ok=True)
        self._sha_index: Dict[str, Dict[str, str]] = {}

    # -- org -------------------------------------------------------------------------------

    def remaining_core_calls(self) -> Optional[int]:
        try:
            value = gh(["api", "rate_limit", "--jq", ".resources.core.remaining"], raw=True)
            return int(value.strip())
        except (GhError, ValueError):
            return None

    def list_repos(self) -> List[RepoInfo]:
        listing = self.cache_dir / "org" / self.org / "repos.json"
        if self.offline or (listing.exists() and not self.refresh):
            if not listing.exists():
                raise GhError(f"--offline but no cached repo list at {listing}")
            rows = json.loads(listing.read_text(encoding="utf-8"))
        else:
            text = gh(
                ["api", f"orgs/{self.org}/repos", "--paginate", "--jq",
                 ".[] | {name, private, size, default_branch, archived}"],
                raw=True,
            )
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            listing.parent.mkdir(parents=True, exist_ok=True)
            listing.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        repos = []
        for row in sorted(rows, key=lambda r: r["name"].lower()):
            repos.append(RepoInfo(
                name=row["name"],
                private=bool(row.get("private", True)),
                size=int(row.get("size") or 0),
                default_branch=row.get("default_branch") or "main",
                archived=bool(row.get("archived", False)),
            ))
        return repos

    # -- one repo ------------------------------------------------------------------------

    def load_tree(self, repo: RepoInfo) -> RepoInfo:
        """Pin HEAD and load the recursive tree into ``repo.files`` (cached per repo)."""
        cache_file = self.repo_cache / f"{repo.name}.json"
        if repo.size == 0:
            repo.error = "empty repository"
            return repo
        if cache_file.exists() and not self.refresh:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
        elif self.offline:
            repo.error = "not in cache (--offline)"
            return repo
        else:
            try:
                head = gh(["api", f"repos/{self.org}/{repo.name}/commits/{encode_branch(repo.default_branch)}",
                           "--jq", "{sha: .sha, tree: .commit.tree.sha}"])
                tree = gh(["api", f"repos/{self.org}/{repo.name}/git/trees/{head['tree']}?recursive=1"])
            except GhEmptyRepo:
                repo.error = "empty repository"
                return repo
            except GhError as exc:
                repo.error = f"fetch failed: {exc}"
                logger.warning("%s: %s", repo.name, repo.error)
                return repo
            data = {
                "head_sha": head["sha"],
                "truncated": bool(tree.get("truncated")),
                "files": {
                    item["path"]: [item["sha"], int(item.get("size") or 0)]
                    for item in tree.get("tree", []) if item.get("type") == "blob"
                },
            }
            cache_file.write_text(json.dumps(data, indent=1), encoding="utf-8")
        repo.head_sha = data["head_sha"]
        repo.truncated = data["truncated"]
        repo.files = {path: meta[1] for path, meta in data["files"].items()}
        self._sha_index[repo.name] = {path: meta[0] for path, meta in data["files"].items()}
        return repo

    def blob_id(self, repo: RepoInfo, path: str) -> Optional[str]:
        return self._sha_index.get(repo.name, {}).get(path)

    def read(self, repo: RepoInfo, path: str) -> Optional[str]:
        sha = self.blob_id(repo, path)
        if not sha:
            return None
        cached = self.blob_cache / sha
        if cached.exists():
            return cached.read_bytes().decode("utf-8", errors="replace")
        if self.offline:
            return None
        try:
            blob = gh(["api", f"repos/{self.org}/{repo.name}/git/blobs/{sha}"])
        except GhError as exc:
            logger.warning("%s:%s blob fetch failed: %s", repo.name, path, exc)
            return None
        data = base64.b64decode((blob.get("content") or "").replace("\n", ""))
        cached.write_bytes(data)
        return data.decode("utf-8", errors="replace")

    def web_url(self, repo: RepoInfo, path: str, line: Optional[int] = None) -> str:
        anchor = f"#L{line}" if line else ""
        return f"https://github.com/{self.org}/{repo.name}/blob/{repo.head_sha}/{quote(path)}{anchor}"


class LocalSource:
    """Reads repos from local directories (fixtures, or a single repo via --path)."""

    kind = "local"

    def __init__(self, org: str, root: Path, meta: Optional[List[Dict[str, Any]]] = None) -> None:
        self.org = org
        self.root = root
        self.meta = meta  # None -> every subdirectory of root is a repo

    @classmethod
    def single(cls, path: Path) -> "LocalSource":
        path = path.resolve()
        return cls("local", path.parent, meta=[{"name": path.name, "private": True}])

    @classmethod
    def fixtures(cls, org_file: Path, repos_dir: Path) -> "LocalSource":
        spec = json.loads(org_file.read_text(encoding="utf-8"))
        return cls(spec["org"], repos_dir, meta=spec["repos"])

    def remaining_core_calls(self) -> Optional[int]:
        return None

    def list_repos(self) -> List[RepoInfo]:
        rows = self.meta
        if rows is None:
            rows = [{"name": p.name} for p in sorted(self.root.iterdir()) if p.is_dir()]
        repos = []
        for row in rows:
            exists = (self.root / row["name"]).is_dir()
            repos.append(RepoInfo(
                name=row["name"],
                private=bool(row.get("private", True)),
                size=int(row.get("size", 1 if exists else 0)),
                default_branch=row.get("default_branch", "main"),
                archived=bool(row.get("archived", False)),
            ))
        return repos

    def load_tree(self, repo: RepoInfo) -> RepoInfo:
        base = self.root / repo.name
        if repo.size == 0 or not base.is_dir():
            repo.error = "empty repository"
            return repo
        files: Dict[str, int] = {}
        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(base).parts):
                continue
            files[path.relative_to(base).as_posix()] = path.stat().st_size
        digest = hashlib.sha256(json.dumps(sorted(files.items())).encode("utf-8")).hexdigest()
        repo.files = files
        repo.head_sha = f"local-{digest[:12]}"
        return repo

    def read(self, repo: RepoInfo, path: str) -> Optional[str]:
        target = self.root / repo.name / path
        if not target.is_file():
            return None
        return target.read_bytes().decode("utf-8", errors="replace")

    def web_url(self, repo: RepoInfo, path: str, line: Optional[int] = None) -> str:
        anchor = f"#L{line}" if line else ""
        return f"{repo.name}/{path}{anchor}"
