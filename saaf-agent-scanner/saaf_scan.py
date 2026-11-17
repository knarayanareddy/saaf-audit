#!/usr/bin/env python3
"""SAAF agent scanner — read-only static checks for weakness classes found across SAAF repositories.

Usage:
    python3 -I saaf_scan.py <repo-dir> [<repo-dir> ...] [--out DIR] [--team NAME] [--only ID,ID] [--include-tests]
    python3 -I saaf_scan.py --list

Output (in --out, default ./saaf-scan-out):
    findings.csv   SAAF submission columns: title,repo,risk_rating,observation,recommendation,verified,team
    findings.json  every hit with path:line and evidence
    summary.md     per-check and per-repo overview + prevalence across scanned repos

Exit code: 0 = no findings at/above --fail-on (default: never fail), 1 = findings at/above threshold.

Design rules:
  * Read-only. Never imports, installs or executes code from the scanned repository; only reads files
    and runs read-only git commands (git log/rev-parse) when --history is given.
  * Stdlib only. Checks are plain modules in ./checks, loaded from this tool's directory, never from the target.
  * One finding per check per repository (same root cause in one repo counts once); all locations listed.
  * Every finding is a CANDIDATE: verified=no until a human or the triage skill confirms it.
"""
from __future__ import annotations

import argparse, csv, importlib.util, json, os, re, subprocess, sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOL_DIR / "checks"))  # tool-local helpers only, never the target repo
from _lib import Hit, snippet, redact  # noqa: E402
SEVERITY = ["Info", "Low", "Medium", "High", "Critical"]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "dist", "build", "site-packages", "__pycache__",
             ".mypy_cache", ".pytest_cache", ".tox", ".next", "vendor", "coverage"}
TEST_DIR_RE = re.compile(r"(^|/)(tests?|testing|fixtures?|__tests__|spec|examples?)(/|$)", re.I)
TEXT_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".yaml", ".yml", ".toml", ".md", ".txt",
            ".html", ".htm", ".cfg", ".ini", ".env", ".sh", ".j2", ".jinja", ".vue", ".svelte"}
MAX_BYTES = 1_000_000


@dataclass
class Repo:
    root: Path
    include_tests: bool = False
    history: bool = False
    _cache: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.root.name

    def commit(self) -> str:
        try:
            return subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"], capture_output=True,
                                  text=True, timeout=10).stdout.strip()
        except Exception:
            return ""

    def files(self, exts: set[str] | tuple[str, ...] | None = None, names: set[str] | None = None):
        """Yield repo-relative POSIX paths of text files (skips vendored dirs, symlinks, big files, tests)."""
        if "all" not in self._cache:
            out = []
            for dp, dns, fns in os.walk(self.root, followlinks=False):
                dns[:] = [d for d in dns if d not in SKIP_DIRS]
                for fn in fns:
                    p = Path(dp) / fn
                    if p.is_symlink():
                        continue
                    rel = p.relative_to(self.root).as_posix()
                    if not self.include_tests and TEST_DIR_RE.search(rel):
                        continue
                    try:
                        if p.stat().st_size > MAX_BYTES:
                            continue
                    except OSError:
                        continue
                    out.append(rel)
            self._cache["all"] = sorted(out)
        for rel in self._cache["all"]:
            low = rel.lower()
            base = low.rsplit("/", 1)[-1]
            if names and base in names:
                yield rel
            elif exts and any(low.endswith(e) for e in exts):
                yield rel
            elif not exts and not names and Path(low).suffix in TEXT_EXT:
                yield rel

    def read(self, rel: str) -> str:
        if rel not in self._cache:
            try:
                self._cache[rel] = (self.root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._cache[rel] = ""
        return self._cache[rel]

    def lines(self, rel: str) -> list[str]:
        return self.read(rel).splitlines()

    def grep(self, pattern: str | re.Pattern, exts=None, flags=0):
        """Yield (rel, lineno, line, match) for every line matching pattern."""
        rx = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
        for rel in self.files(exts):
            for i, line in enumerate(self.lines(rel), 1):
                m = rx.search(line)
                if m:
                    yield rel, i, line, m

    def git_log_patch(self, max_bytes: int = 30_000_000) -> str:
        """Full patch history of all refs (read-only). Only when --history is enabled."""
        if not self.history:
            return ""
        if "gitlog" not in self._cache:
            try:
                r = subprocess.run(["git", "-C", str(self.root), "log", "--all", "-p", "--no-color", "--no-ext-diff",
                                    "--format=@@COMMIT %H"], capture_output=True, text=True, timeout=180,
                                   errors="replace")
                self._cache["gitlog"] = r.stdout[:max_bytes]
            except Exception:
                self._cache["gitlog"] = ""
        return self._cache["gitlog"]


def load_checks(only: set[str] | None = None):
    checks = []
    for p in sorted((TOOL_DIR / "checks").glob("*.py")):
        if p.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"saaf_checks.{p.stem}", p)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:  # one broken check must not disable the others
            print(f"[warn] could not load check {p.name}: {e}", file=sys.stderr)
            continue
        meta = getattr(mod, "CHECK", None)
        if not meta or not hasattr(mod, "run"):
            continue
        if only and meta["id"] not in only:
            continue
        checks.append((meta, mod.run))
    return checks


def scan(repo_dirs, only=None, include_tests=False, history=False):
    checks = load_checks(only)
    results = []   # one entry per (repo, check) with hits
    for d in repo_dirs:
        repo = Repo(Path(d).resolve(), include_tests=include_tests, history=history)
        commit = repo.commit()
        for meta, run in checks:
            try:
                hits = run(repo) or []
            except Exception as e:  # a broken check must not stop the scan
                print(f"[warn] {meta['id']} failed on {repo.name}: {e}", file=sys.stderr)
                continue
            if hits:
                results.append({"repo": repo.name, "commit": commit, "check": meta,
                                "hits": [asdict(h) for h in hits[:50]], "hit_count": len(hits)})
    return checks, results


def write_outputs(checks, results, out: Path, team: str, n_repos: int):
    out.mkdir(parents=True, exist_ok=True)
    by_check: dict[str, set[str]] = {}
    for r in results:
        by_check.setdefault(r["check"]["id"], set()).add(r["repo"])

    rows = []
    for r in sorted(results, key=lambda x: (-SEVERITY.index(x["check"]["severity"]), x["repo"], x["check"]["id"])):
        c, hits = r["check"], r["hits"]
        locs = "\n".join(f"- {h['path']}:{h['line']}: {h['evidence']}" + (f"  ({h['detail']})" if h['detail'] else "")
                         for h in hits[:10])
        more = f"\n- ... and {r['hit_count'] - 10} more locations" if r["hit_count"] > 10 else ""
        others = sorted(by_check[c["id"]] - {r["repo"]})
        prevalence = (f"Prevalence: this check ({c['id']} {c['slug']}) matched {len(by_check[c['id']])} of {n_repos} "
                      f"scanned repositories" + (f"; also in: {', '.join(others)}." if others else "."))
        obs = (f"Repository: {r['repo']} @ {r['commit'][:12]}\n\n"
               f"Intended behaviour: {c['intended']}\nActual: {c['actual']}\nImpact: {c['impact']}\n\n"
               f"Locations ({r['hit_count']}):\n{locs}{more}\n\n"
               f"Detected by the SAAF agent scanner (static pattern check {c['id']}, {c.get('refs', '')}). "
               f"Candidate finding: confirm reachability and impact before reporting as verified.\n{prevalence}")
        rows.append({"title": c["title"], "repo": r["repo"], "risk_rating": c["severity"], "observation": obs,
                     "recommendation": c["recommendation"], "verified": "no", "team": team})

    with (out / "findings.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["title", "repo", "risk_rating", "observation", "recommendation",
                                           "verified", "team"], quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(rows)
    (out / "findings.json").write_text(json.dumps(results, indent=2))

    md = [f"# SAAF agent scanner results", "", f"Repositories scanned: {n_repos}. Candidate findings: {len(rows)}.",
          "All results are candidates (verified=no) until triaged.", "",
          "| check | severity | title | repos matched | % |", "|---|---|---|---|---|"]
    for meta, _ in checks:
        rs = by_check.get(meta["id"], set())
        md.append(f"| {meta['id']} {meta['slug']} | {meta['severity']} | {meta['title']} | {len(rs)} | "
                  f"{100 * len(rs) // max(n_repos, 1)}% |")
    md += ["", "## Per repository", "", "| repo | candidates | checks |", "|---|---|---|"]
    per = {}
    for r in results:
        per.setdefault(r["repo"], []).append(r["check"]["id"])
    for repo, ids in sorted(per.items(), key=lambda x: -len(x[1])):
        md.append(f"| {repo} | {len(ids)} | {', '.join(sorted(ids))} |")
    (out / "summary.md").write_text("\n".join(md) + "\n")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--out", default="saaf-scan-out")
    ap.add_argument("--team", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--include-tests", action="store_true", help="also scan tests/ fixtures/ examples/")
    ap.add_argument("--history", action="store_true", help="also scan full git history (secrets checks)")
    ap.add_argument("--fail-on", choices=SEVERITY, help="exit 1 if any finding at/above this severity")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for meta, _ in load_checks():
            print(f"{meta['id']}  {meta['severity']:8} {meta['category']:34} {meta['title']}")
        return 0
    if not a.repos:
        ap.error("give at least one repository directory")
    only = {x.strip() for x in a.only.split(",") if x.strip()} or None
    checks, results = scan(a.repos, only, a.include_tests, a.history)
    rows = write_outputs(checks, results, Path(a.out), a.team, len(a.repos))
    print(f"{len(rows)} candidate findings in {len(a.repos)} repos -> {a.out}/findings.csv, summary.md")
    if a.fail_on and any(SEVERITY.index(r["risk_rating"]) >= SEVERITY.index(a.fail_on) for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
