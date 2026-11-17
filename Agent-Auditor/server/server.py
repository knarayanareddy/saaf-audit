"""
Agent Auditor — local evaluator server (GitHub-target editie).

De browser-UI (audit-criteria-sheet.html) configureert via deze server een
GitHub-repo + commit als auditdoel. Bestanden, commits en issues worden
allemaal via de GitHub-API opgehaald — er is geen lokale clone meer.
Claude wordt aangeroepen via de Claude Agent SDK, die op zijn beurt de
authenticatie van Claude Code hergebruikt.

Endpoints:
    GET  /ping              gezondheids- en configuratiecheck
    POST /configure-target  owner/repo/ref instellen, bestanden ophalen
    POST /list-commits      laatste commits voor de picker
    POST /reload            target opnieuw ophalen
    POST /evaluate          één acceptance criterium beoordelen
    POST /audit-trail       audit-trail bouwen voor de target-repo
    POST /log               auditor-actie loggen
    GET  /log               laatste log-entries lezen

Start:
    python -m pip install -r requirements.txt
    python server.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "\n[server] claude-agent-sdk niet gevonden. Installeer met:\n"
        "    python -m pip install -r requirements.txt\n\n"
    )
    raise

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger("agent-auditor")

ROOT = Path(__file__).resolve().parent.parent
LOCK_FILE = ROOT / "repo.lock.json"
AUDIT_CACHE_FILE = ROOT / "audit-trail.cache.json"
ACTIONS_LOG = ROOT / "actions.log.jsonl"
ORGS_FILE = ROOT / "orgs.json"            # D-1: multi-org dashboard state
METRICS_CACHE_DIR = ROOT / ".metrics"     # D-4: per-repo audit-summary cache


# ---------------------------------------------------------------------------
# Versie + build
# ---------------------------------------------------------------------------

TOOL_VERSION = "0.5.0"
SERVER_BUILD = "2026-06-17-ac-summary-sync"


# ---------------------------------------------------------------------------
# Hashing + helpers (P-2, P-3, P-5)
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_bundle(files: dict[str, str]) -> tuple[str, dict[str, str]]:
    per_file = {name: _sha256(content) for name, content in files.items()}
    combined = "\n".join(f"{name}:{per_file[name]}" for name in sorted(per_file))
    return _sha256(combined), per_file


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

GH_URL_RE = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
ISSUE_REF_RE = re.compile(r"#(\d+)")
CLOSING_RE = re.compile(r"(?i)\b(close[ds]?|fix(?:es|ed)?|resolve[sd]?)\s+#(\d+)")


def parse_github_remote(url: Optional[str]) -> Optional[tuple[str, str]]:
    if not url:
        return None
    m = GH_URL_RE.search(url)
    return (m.group(1), m.group(2)) if m else None


def github_token() -> Optional[str]:
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        v = os.environ.get(var)
        if v:
            return v
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


async def gh_get(path: str) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = github_token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    async with httpx.AsyncClient(timeout=30.0) as cli:
        r = await cli.get(f"https://api.github.com{path}", headers=headers)
    if r.status_code == 404:
        return None
    if r.status_code == 403:
        raise RuntimeError("GitHub API 403 — rate limit of geen toegang. Stel GITHUB_TOKEN in of doe `gh auth login`.")
    if r.status_code != 200:
        raise RuntimeError(f"GitHub API {r.status_code}: {r.text[:200]}")
    return r.json()


async def gh_resolve_ref(owner: str, repo: str, ref: str) -> dict:
    """Vertaal een branch/tag/SHA naar een concrete commit. Levert
    {sha, short_sha, message, date, author, branch}."""
    # Probeer eerst als commit (SHA of korte SHA werken beide via /commits/{ref})
    data = await gh_get(f"/repos/{owner}/{repo}/commits/{ref}")
    if not data:
        raise RuntimeError(f"Ref '{ref}' niet gevonden op {owner}/{repo}.")
    sha = data["sha"]
    return {
        "sha": sha,
        "short_sha": sha[:7],
        "message": data["commit"]["message"],
        "subject": data["commit"]["message"].split("\n", 1)[0],
        "date": data["commit"]["author"]["date"],
        "author": f"{data['commit']['author']['name']} <{data['commit']['author']['email']}>",
        "ref_input": ref,
    }


async def gh_list_default_branch(owner: str, repo: str) -> str:
    data = await gh_get(f"/repos/{owner}/{repo}")
    if not data:
        raise RuntimeError(f"Repo {owner}/{repo} niet gevonden.")
    return data.get("default_branch") or "main"


async def gh_get_tree(owner: str, repo: str, sha: str) -> list[dict]:
    data = await gh_get(f"/repos/{owner}/{repo}/git/trees/{sha}?recursive=1")
    if not data:
        return []
    return data.get("tree", [])


async def gh_get_file(owner: str, repo: str, path: str, ref: str) -> Optional[str]:
    data = await gh_get(f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
    if not data or not isinstance(data, dict):
        return None
    enc = data.get("encoding")
    content = data.get("content") or ""
    if enc == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return None
    return content


async def gh_list_commits(owner: str, repo: str, sha: str, limit: int = 30) -> list[dict]:
    data = await gh_get(f"/repos/{owner}/{repo}/commits?sha={sha}&per_page={min(limit, 100)}")
    if not data:
        return []
    commits = []
    for c in data:
        msg = c["commit"]["message"]
        commits.append({
            "sha": c["sha"],
            "short_sha": c["sha"][:7],
            "author_name": c["commit"]["author"]["name"],
            "author_email": c["commit"]["author"]["email"],
            "date": c["commit"]["author"]["date"],
            "subject": msg.split("\n", 1)[0],
            "body": msg.split("\n", 1)[1].strip() if "\n" in msg else "",
        })
    return commits


async def gh_get_commit_detail(owner: str, repo: str, sha: str) -> dict:
    """Geef diff-stat + patches voor een specifieke commit, getrunkeerd."""
    data = await gh_get(f"/repos/{owner}/{repo}/commits/{sha}")
    if not data:
        return {"stat": "", "diff": ""}
    files = data.get("files", []) or []
    stat = "\n".join(
        f"  {f.get('filename','?')} | +{f.get('additions',0)} -{f.get('deletions',0)}"
        for f in files[:30]
    )
    patches = []
    for f in files[:10]:
        p = f.get("patch") or ""
        if p:
            patches.append(f"--- {f.get('filename')} ---\n{p[:1000]}")
    return {"stat": stat[:2000], "diff": "\n\n".join(patches)[:8000]}


# ---------------------------------------------------------------------------
# Bestand-discovery — welke bestanden uit de doel-repo moeten naar Claude?
# ---------------------------------------------------------------------------

DEFAULT_FILE_PATTERNS = [
    # Root markdown + scripting
    r"^README(\.md)?$",
    r"^CLAUDE\.md$",
    r"^AGENTS?\.md$",
    r"^architecture\.md$",
    r"^[A-Z_]+\.md$",
    # Root python
    r"^[a-zA-Z_][\w-]*\.py$",
    # Eén niveau diep
    r"^(services|src|app|lib|prompts)/[a-zA-Z_][\w-]*\.py$",
    # docs map
    r"^docs?/[\w-]+\.md$",
]
FILE_SIZE_CAP = 100_000  # 100 KB per file
FILE_TOTAL_CAP = 250_000  # 250 KB totaal (richting Claude)
MAX_FILES = 25


def is_bundleable(path: str, size: int) -> bool:
    if size > FILE_SIZE_CAP:
        return False
    for pat in DEFAULT_FILE_PATTERNS:
        if re.match(pat, path):
            return True
    return False


async def discover_files(owner: str, repo: str, sha: str) -> list[dict]:
    tree = await gh_get_tree(owner, repo, sha)
    candidates = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        size = int(item.get("size") or 0)
        if is_bundleable(path, size):
            candidates.append({"path": path, "size": size})
    # Sorteer op typische relevantie: README/CLAUDE/architecture eerst, dan python
    priority = ("README", "CLAUDE", "AGENT", "architecture")
    candidates.sort(key=lambda c: (0 if any(c["path"].startswith(p) for p in priority) else 1, c["path"]))
    return candidates[:MAX_FILES]


# ---------------------------------------------------------------------------
# Target-state — single source of truth
# ---------------------------------------------------------------------------

TARGET: dict = {
    "configured": False,
    "owner": None,
    "repo": None,
    "ref_input": None,    # wat de gebruiker invoerde
    "sha": None,          # opgelost
    "short_sha": None,
    "branch": None,       # default branch info (informatief)
    "commit_subject": None,
    "commit_date": None,
    "commit_author": None,
    "files": [],          # lijst van paden in de bundel
    "loaded_at": None,
}
REPO_CACHE: dict[str, str] = {}
BUNDLE_HASH: str = ""
FILE_HASHES: dict[str, str] = {}


def current_provenance() -> dict:
    """Bouw provenance-blok uit TARGET — vervangt de oude lokale-git aanpak."""
    if not TARGET["configured"]:
        return {"available": False, "reason": "Geen target geconfigureerd."}
    return {
        "available": True,
        "captured_at": TARGET["loaded_at"],
        "remote": f"https://github.com/{TARGET['owner']}/{TARGET['repo']}",
        "branch": TARGET["branch"],
        "commit": TARGET["sha"],
        "commit_short": TARGET["short_sha"],
        "commit_date": TARGET["commit_date"],
        "commit_message": TARGET["commit_subject"],
        "author": TARGET["commit_author"],
        "dirty": False,  # GitHub-staat is per definitie clean tegen de commit
        "ref_input": TARGET["ref_input"],
    }


def write_lock() -> None:
    try:
        LOCK_FILE.write_text(
            json.dumps(current_provenance(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        log.warning("Kon repo.lock.json niet schrijven: %s", e)


async def load_target(owner: str, repo: str, ref: Optional[str], file_paths: Optional[list[str]] = None) -> dict:
    """Configureer target: resolve ref, ontdek bestanden, vul REPO_CACHE."""
    global REPO_CACHE, BUNDLE_HASH, FILE_HASHES
    if not ref:
        ref = await gh_list_default_branch(owner, repo)
    commit = await gh_resolve_ref(owner, repo, ref)
    sha = commit["sha"]

    # Bestanden bepalen: expliciete lijst, of auto-discover
    if file_paths:
        files_to_fetch = file_paths[:MAX_FILES]
    else:
        discovered = await discover_files(owner, repo, sha)
        files_to_fetch = [d["path"] for d in discovered]

    new_cache: dict[str, str] = {}
    total_size = 0
    for path in files_to_fetch:
        content = await gh_get_file(owner, repo, path, sha)
        if content is None:
            log.warning("Kon %s niet ophalen", path)
            continue
        if total_size + len(content) > FILE_TOTAL_CAP:
            log.info("Bundle-cap bereikt; sla %s over", path)
            break
        new_cache[path] = content
        total_size += len(content)

    REPO_CACHE = new_cache
    BUNDLE_HASH, FILE_HASHES = hash_bundle(REPO_CACHE)

    TARGET.update({
        "configured": True,
        "owner": owner,
        "repo": repo,
        "ref_input": ref,
        "sha": sha,
        "short_sha": sha[:7],
        "branch": ref if "/" not in ref and not re.fullmatch(r"[0-9a-f]{7,40}", ref) else None,
        "commit_subject": commit["subject"],
        "commit_date": commit["date"],
        "commit_author": commit["author"],
        "files": list(REPO_CACHE.keys()),
        "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    write_lock()
    log.info("Target geladen: %s/%s @ %s — %d bestanden (%d bytes)", owner, repo, sha[:7], len(REPO_CACHE), total_size)
    return TARGET


# ---------------------------------------------------------------------------
# Audit-log (P-1)
# ---------------------------------------------------------------------------


def log_event(event_type: str, payload: dict) -> None:
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "type": event_type,
            "tool_version": TOOL_VERSION,
            "commit": TARGET.get("sha"),
            "bundle_hash": BUNDLE_HASH,
            "payload": payload,
        }
        with ACTIONS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        log.warning("Kon actions.log.jsonl niet schrijven: %s", e)


# ---------------------------------------------------------------------------
# Bundle XML + evidence validatie (P-4, P-6)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Secrets-scan (F-1) — detecteer hardcoded API-keys/tokens/private keys in
# de bundel. Findings worden als auto-bevindingen in /audit-trail getoond.
# ---------------------------------------------------------------------------

SECRET_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, label, severity)
    (r"sk-ant-[a-zA-Z0-9_-]{20,}",                     "Anthropic API-key",     "high"),
    (r"sk-(?:proj-)?[a-zA-Z0-9]{40,}",                 "OpenAI API-key",        "high"),
    (r"\bgh[opasu]_[A-Za-z0-9]{36,}\b",                "GitHub token",          "high"),
    (r"\bAKIA[0-9A-Z]{16}\b",                          "AWS access key ID",     "high"),
    (r"\bASIA[0-9A-Z]{16}\b",                          "AWS temporary key",     "high"),
    (r"\bxox[bpoars]-[a-zA-Z0-9-]+",                   "Slack token",           "high"),
    (r"\bAIza[0-9A-Za-z_-]{35}\b",                     "Google API-key",        "high"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", "Private key (PEM)", "high"),
    (r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key|client[_-]?secret|aws[_-]?secret(?:_access)?_key|bearer[_-]?token|auth[_-]?token|password|passwd|connection[_-]?string)\s*[:=]\s*['\"][^'\"\\s$<>{}]{8,}['\"]",
                                                       "Hardcoded credential",  "medium"),
    (r"(?i)mongodb(?:\+srv)?://[^:]+:[^@\s]+@",        "MongoDB connection-string with password", "high"),
    (r"(?i)postgres(?:ql)?://[^:]+:[^@\s]+@",          "Postgres connection-string with password", "high"),
]

# Bestanden waar matches typisch placeholders zijn — niet als finding rapporteren
FALSE_POSITIVE_PATH_PATTERNS = [
    r"(?i)example",
    r"(?i)\.sample\b",
    r"(?i)\.template\b",
    r"(?i)/fixtures?/",
    r"(?i)/tests?/",
    r"(?i)\.lock\.json$",
    r"(?i)\.lock$",
]

# Per-line markers die suggereren dat het om een placeholder gaat
PLACEHOLDER_MARKERS = (
    "your-", "<your", "xxxx", "REPLACE_ME", "REPLACEME", "TODO", "PLACEHOLDER",
    "EXAMPLE", "example.com", "FAKE", "DUMMY", "...", "1234567890",
)


def _looks_like_placeholder(line: str) -> bool:
    upper = line
    return any(m in upper for m in PLACEHOLDER_MARKERS)


def _path_is_example(path: str) -> bool:
    for pat in FALSE_POSITIVE_PATH_PATTERNS:
        if re.search(pat, path):
            return True
    return False


def scan_bundle_for_secrets(repo_cache: dict[str, str]) -> list[dict]:
    """Loop alle bundle-bestanden door en flag potentiële secrets.
    False-positive-onderdrukking op typische voorbeeld-bestanden en
    placeholder-markers ('your-', 'xxxx', 'example.com')."""
    findings: list[dict] = []
    for path, content in repo_cache.items():
        path_is_example = _path_is_example(path)
        for line_no, line in enumerate(content.splitlines(), start=1):
            if len(line) > 600:
                continue  # extreem lange regels (minified/blob) overslaan
            for pattern, label, severity in SECRET_PATTERNS:
                m = re.search(pattern, line)
                if not m:
                    continue
                placeholder = _looks_like_placeholder(line)
                snippet = line.strip()
                if len(snippet) > 180:
                    # Trim rond de match
                    s = max(0, m.start() - 60)
                    snippet = "…" + line[s:m.end() + 60].strip() + "…"
                findings.append({
                    "file": path,
                    "line": line_no,
                    "kind": label,
                    "severity": severity if not (path_is_example or placeholder) else "low",
                    "snippet": snippet,
                    "is_example": path_is_example or placeholder,
                    "match_preview": line[m.start():m.end()][:40] + ("…" if m.end() - m.start() > 40 else ""),
                })
                break  # één pattern per regel is genoeg
    return findings


def build_repo_xml(exclude: Optional[set[str]] = None) -> str:
    excl = exclude or set()
    return "\n\n".join(
        f'<file path="{name}">\n{content}\n</file>'
        for name, content in REPO_CACHE.items()
        if name not in excl
    )


def effective_bundle_hash(exclude: Optional[set[str]] = None) -> str:
    if not exclude:
        return BUNDLE_HASH
    included = {n: c for n, c in REPO_CACHE.items() if n not in exclude}
    h, _ = hash_bundle(included)
    return h


def _normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def validate_evidence(evidence_items: list[dict]) -> tuple[list[dict], dict]:
    enriched: list[dict] = []
    n_total = n_valid = n_no_file = n_no_match = 0
    for item in evidence_items or []:
        if not isinstance(item, dict):
            continue
        file_ = (item.get("file") or "").strip()
        quote = (item.get("quote") or "").strip()
        out = dict(item)
        if not quote:
            out["validated"] = None
            out["validation_note"] = "Geen quote opgegeven."
            enriched.append(out)
            continue
        n_total += 1
        content = REPO_CACHE.get(file_)
        if content is None:
            out["validated"] = False
            out["validation_note"] = f"Bestand '{file_}' staat niet in de bundle."
            n_no_file += 1
            enriched.append(out)
            continue
        haystack = _normalize_for_match(content).lower()
        needle = _normalize_for_match(quote).lower()
        is_match = bool(needle) and needle in haystack
        out["validated"] = is_match
        if is_match:
            n_valid += 1
            out["validation_note"] = None
        else:
            n_no_match += 1
            out["validation_note"] = "Quote niet letterlijk in bestand — mogelijke hallucinatie of parafrase."
        enriched.append(out)
    summary = {
        "total": n_total,
        "validated": n_valid,
        "no_match": n_no_match,
        "no_file_in_bundle": n_no_file,
        "all_hallucinated": bool(n_total) and n_valid == 0,
    }
    return enriched, summary


def extract_json(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        body = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if "```" in body:
            body = body.rsplit("```", 1)[0]
        raw = body.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("Geen JSON-object gevonden in respons")
    return json.loads(raw[start:end + 1])


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_EVAL = """Je bent een ervaren IT-auditor (Vaktechniek) die de OPZET van een AI-agent beoordeelt tegen een acceptance criterium uit een audit-criteria-sheet.

Je krijgt:
- De broncode en documentatie van de agent (in <repo> tags binnen het user-bericht)
- Eén acceptance criterium met bijbehorend control objective en framework-context

Je taak: bepaal of de AGENT ZOALS NU OPGEZET (broncode + prompts + schema) dit criterium structureel zou halen. Beoordeel de OPZET, niet een specifieke run-output.

Verdicts:
- "pass"    = de opzet borgt het criterium aantoonbaar (prompt-instructie, schema-constraint, code-flow)
- "fail"    = de opzet borgt het criterium aantoonbaar niet, of een implementatie-omissie maakt het onhaalbaar
- "na"      = het criterium is niet van toepassing op deze opzet
- "unknown" = onvoldoende basis om te oordelen vanuit alleen de opzet (vereist runtime-observatie)

Wees streng over hallucinatie: refereer alleen naar bestanden/regels die je daadwerkelijk in <repo> ziet. Geen aannames. Liever "unknown" dan gokken.

Antwoord UITSLUITEND met een geldig JSON-object met deze velden:
{
  "verdict": "pass" | "fail" | "na" | "unknown",
  "reasoning": "2-4 zinnen onderbouwing, in het Nederlands",
  "evidence": [
    { "file": "bestandsnaam", "lines": "regelnummers of sectie", "quote": "letterlijk fragment uit de repo" }
  ]
}

Begin direct met { — geen markdown fence, geen tekst eromheen."""

PROMPT_HASH_EVAL = _sha256(SYSTEM_PROMPT_EVAL)


SYSTEM_PROMPT_AUDIT = """Je bent een IT-auditor die beoordeelt of een GitHub Issue (bevinding) adequaat is opgevolgd in een agent-repo.

Je krijgt:
1. Het issue (titel, body, labels, status) — dit is de bevinding.
2. De commit die het issue claimt te sluiten (of geen, als nog niet opgevolgd) inclusief diff.
3. De huidige staat van de repo (in <repo>-tags) ter context.

Beoordeel of:
- de codewijzigingen aantoonbaar de bevinding adresseren (oorzaak, niet alleen symptoom);
- er borging is (tests, CI, documentatie, schema-constraint);
- de scope van de commit consistent is met de scope van de bevinding;
- de fix in de huidige repo-staat nog steeds aanwezig is.

Bij een issue ZONDER closing-commit beoordeel je of de bevinding via een andere route is geadresseerd in de huidige repo-staat (bv. duplicate verwijderd, test toegevoegd in een commit zonder issue-ref). Dat wijst op een traceerbaarheidsgap (gefixt buiten het issue-proces om).

Verdicts:
- "adequate"   = bevinding compleet en adequaat opgelost, met passende borging
- "partial"    = deels opgelost; oorzaak of borging onvolledig
- "inadequate" = niet wezenlijk opgelost; scope-mismatch, cosmetisch, of fix verdwenen
- "open"       = nog geen opvolging zichtbaar in de repo
- "unrelated"  = de geclaimde commit raakt het issue niet

Antwoord UITSLUITEND met geldig JSON:
{
  "verdict": "adequate" | "partial" | "inadequate" | "open" | "unrelated",
  "reasoning": "NL, 2-4 zinnen onderbouwing",
  "evidence": [{"file": "...", "lines": "...", "quote": "fragment uit diff of repo"}],
  "follow_up_required": ["concrete vervolgactie 1", "..."]
}

Begin direct met { — geen markdown fence, geen tekst eromheen."""

PROMPT_HASH_AUDIT = _sha256(SYSTEM_PROMPT_AUDIT)


SYSTEM_PROMPT_ORPHAN = """Je bent een IT-auditor die beoordeelt of een commit die GEEN GitHub Issue referenceert via het issue-proces had moeten lopen.

Je krijgt een commit (subject, body, diff-stat) zonder issue-koppeling. Antwoord met:
- "needs_issue"   = inhoudelijke wijziging (feature/fix) die volgens een normaal traceerbaarheidsproces door een issue had moeten lopen
- "acceptable"    = legitieme onderhoudscommit (docs, refactor van eigen werk, typo, formatting, version bump)
- "unclear"       = onvoldoende basis vanuit alleen subject+stat om te oordelen

Antwoord UITSLUITEND met geldig JSON:
{
  "verdict": "needs_issue" | "acceptable" | "unclear",
  "reasoning": "1-2 zinnen NL"
}

Begin direct met { — geen markdown fence, geen tekst eromheen."""

PROMPT_HASH_ORPHAN = _sha256(SYSTEM_PROMPT_ORPHAN)


SYSTEM_PROMPT_CLASSIFY = """Je bepaalt of een GitHub-repo een AI-agent bevat aan de hand van de README.

Een 'agent' in deze context is een autonoom of half-autonoom AI-systeem dat een afgebakende taak uitvoert — typisch met een LLM (Claude/GPT/etc.), een toolchain en een output-format. Voorbeelden: een policy-to-controls extractor, een vulnerability-classifier, een GDPR-audit-agent, een continuous-monitoring agent.

GEEN agent zijn typisch: portal/dashboard-websites, leeg of placeholder-repos, libraries/SDK's die alleen building blocks leveren zonder agentische taak, persoonlijke configuraties, courseware/tutorials.

Antwoord UITSLUITEND met geldig JSON:
{
  "verdict": "agent" | "not_agent" | "unclear",
  "reasoning": "1-2 zinnen NL",
  "agent_signals": ["lijst korte signalen, bv. 'gebruikt anthropic SDK', 'heeft systeemprompt', 'CLI met taak X'"]
}

Begin direct met { — geen markdown fence, geen tekst eromheen."""

PROMPT_HASH_CLASSIFY = _sha256(SYSTEM_PROMPT_CLASSIFY)


SYSTEM_PROMPT_AUTOFIX = """Je stelt voor één audit-bevinding een minimale, realistische fix voor op een AI-agent.

Antwoord UITSLUITEND met geldig JSON:
{
  "title": "korte titel van de fix",
  "root_cause": "1 zin oorzaak",
  "proposed_change": "wat moet er minimaal veranderen — vrije tekst, geen volledige code-blokken (alleen kleine snippets als illustratie)",
  "files_likely_affected": ["pad/naar/file.py", "..."],
  "verification": "hoe iemand achteraf kan verifiëren dat het opgelost is",
  "complexity": "trivial" | "moderate" | "research"
}

Wees eerlijk: als de fix daadwerkelijk complex is (research level), zeg dat dan en stel een onderzoeksstap voor i.p.v. een code-wijziging. Begin direct met { — geen markdown fence."""

PROMPT_HASH_AUTOFIX = _sha256(SYSTEM_PROMPT_AUTOFIX)


# ---------------------------------------------------------------------------
# D-5: GitHub write-helpers (branch maken, file pushen)
# ---------------------------------------------------------------------------


def slugify_reviewer(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", (name or "").strip()).strip("-")
    return s or "unknown"


def make_audit_branch_name(reviewer: str) -> str:
    slug = slugify_reviewer(reviewer)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"auditedby_{slug}_{date}"


async def gh_post(path: str, body: dict) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = github_token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    async with httpx.AsyncClient(timeout=30.0) as cli:
        r = await cli.post(f"https://api.github.com{path}", headers=headers, json=body)
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 403:
        raise RuntimeError("GitHub API 403 — geen schrijfrechten op deze repo. Token mist `repo`-scope of je bent geen collaborator.")
    raise RuntimeError(f"GitHub API {r.status_code}: {r.text[:300]}")


async def gh_put(path: str, body: dict) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = github_token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    async with httpx.AsyncClient(timeout=30.0) as cli:
        r = await cli.put(f"https://api.github.com{path}", headers=headers, json=body)
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 403:
        raise RuntimeError("GitHub API 403 — geen schrijfrechten op deze repo.")
    raise RuntimeError(f"GitHub API {r.status_code}: {r.text[:300]}")


async def gh_create_branch(owner: str, repo: str, branch: str, from_sha: str) -> dict:
    return await gh_post(
        f"/repos/{owner}/{repo}/git/refs",
        {"ref": f"refs/heads/{branch}", "sha": from_sha},
    )


async def gh_put_file(owner: str, repo: str, branch: str, path: str, content: str, message: str) -> dict:
    existing = await gh_get(f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if existing and isinstance(existing, dict) and "sha" in existing:
        body["sha"] = existing["sha"]
    return await gh_put(f"/repos/{owner}/{repo}/contents/{path}", body)


async def propose_fix(finding_text: str, model: Optional[str]) -> dict:
    """Vraag Claude voor één bevinding een minimale fix-voorstel."""
    prompt = f"Audit-bevinding:\n\n{finding_text}\n\nFormuleer een minimale fix als JSON."
    try:
        raw = await run_claude(prompt, model, system_prompt=SYSTEM_PROMPT_AUTOFIX)
        data = extract_json(raw)
    except Exception as e:
        return {
            "title": "Fix-voorstel niet beschikbaar",
            "root_cause": "AI-call mislukt",
            "proposed_change": f"Handmatig oppakken. Fout: {e}",
            "files_likely_affected": [],
            "verification": "—",
            "complexity": "moderate",
        }
    return data


# ---------------------------------------------------------------------------
# Multi-org storage (D-1)
# ---------------------------------------------------------------------------


def load_orgs() -> dict:
    if not ORGS_FILE.exists():
        return {"version": 1, "updated_at": None, "orgs": []}
    try:
        return json.loads(ORGS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("orgs.json corrupt, start leeg: %s", e)
        return {"version": 1, "updated_at": None, "orgs": []}


def save_orgs(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ORGS_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_org(state: dict, owner: str) -> Optional[dict]:
    for o in state["orgs"]:
        if o["owner"].lower() == owner.lower():
            return o
    return None


def find_repo(org: dict, name: str) -> Optional[dict]:
    for r in org.get("repos", []):
        if r["name"].lower() == name.lower():
            return r
    return None


async def gh_list_org_repos(owner: str) -> list[dict]:
    """Probeer eerst /orgs/{owner}/repos; als 404, val terug op /users/{owner}/repos."""
    data = await gh_get(f"/orgs/{owner}/repos?per_page=100&type=all")
    if data is None:
        data = await gh_get(f"/users/{owner}/repos?per_page=100&type=all")
    if not data:
        return []
    return [
        {"name": r["name"], "default_branch": r.get("default_branch") or "main",
         "description": r.get("description") or "", "private": bool(r.get("private")),
         "archived": bool(r.get("archived")), "stars": r.get("stargazers_count", 0)}
        for r in data
    ]


async def classify_agent(owner: str, repo_name: str, model: Optional[str]) -> dict:
    """Vraag Claude of dit een agent is, op basis van de README."""
    try:
        # Probeer een aantal README-varianten
        readme = None
        for name in ("README.md", "README", "readme.md", "Readme.md"):
            readme = await gh_get_file(owner, repo_name, name, "HEAD")
            if readme:
                break
        if not readme:
            return {"verdict": "unclear", "reasoning": "Geen README gevonden.", "agent_signals": []}
    except Exception as e:
        return {"verdict": "unclear", "reasoning": f"README-fetch mislukt: {e}", "agent_signals": []}

    prompt = (
        f"Repo: {owner}/{repo_name}\n\n"
        f"--- README (tot 8KB) ---\n{readme[:8000]}\n--- einde README ---\n\n"
        f"Is dit een AI-agent volgens de definitie? Antwoord UITSLUITEND met JSON."
    )
    try:
        raw = await run_claude(prompt, model, system_prompt=SYSTEM_PROMPT_CLASSIFY)
        data = extract_json(raw)
    except Exception as e:
        return {"verdict": "unclear", "reasoning": f"Classifier-call mislukt: {e}", "agent_signals": []}
    v = data.get("verdict")
    if v not in ("agent", "not_agent", "unclear"):
        v = "unclear"
    return {
        "verdict": v,
        "reasoning": data.get("reasoning") or "",
        "agent_signals": data.get("agent_signals") or [],
        "classified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model or "claude-sonnet-4-6",
    }


# ---------------------------------------------------------------------------
# User-prompt builders
# ---------------------------------------------------------------------------


def build_user_message(req: "EvalRequest") -> str:
    prov = current_provenance()
    prov_line = ""
    if prov.get("available"):
        prov_line = (
            f"Repo-staat onder beoordeling: commit {prov['commit_short']} "
            f"({prov['commit']}) op {prov['remote']}. "
            f"Laatste commit: \"{prov['commit_message']}\" op {prov['commit_date']}."
        )

    lines = [
        f"Control objective {req.objective_id} — {req.objective_title}",
        f"Frameworks: {req.framework}",
        f"Framework-context: {req.framework_brief}",
        f"Objective statement: {req.objective_statement}",
        "",
        f"Acceptance criterium {req.ac_code}:",
        f'"{req.criterion_text}"',
    ]
    if prov_line:
        lines += ["", prov_line]
    if req.way_of_working:
        lines += [
            "",
            "<team_way_of_working>",
            "Onderstaande markdown is door het AI-agent development team aangeleverd als maatwerk-kader. Gebruik dit om je oordeel te tunen op de specifieke conventies, definities of toleranties van dit team — niet als generieke audit-norm.",
            req.way_of_working.strip()[:6000],
            "</team_way_of_working>",
        ]
    if req.extra_context:
        lines.append(f"Extra auditor-context: {req.extra_context}")
    excl = set(req.exclude_files or [])
    if excl:
        lines.append(f"⚠ Door auditor uitgesloten bestanden: {', '.join(sorted(excl))}.")
    lines += [
        "",
        f"<repo>\n{build_repo_xml(exclude=excl)}\n</repo>",
        "",
        "Beoordeel of de agent-opzet hierboven dit criterium structureel borgt. Antwoord UITSLUITEND met JSON: {verdict, reasoning, evidence:[{file,lines,quote}]}.",
    ]
    return "\n".join(lines)


def build_audit_prompt(issue: dict, closing: Optional[dict], diff: Optional[dict], refs: list[dict], exclude: Optional[set[str]] = None, way_of_working: Optional[str] = None) -> str:
    labels = [l["name"] for l in issue.get("labels", [])] if isinstance(issue.get("labels"), list) else []
    lines = [
        f"Issue #{issue['number']}: {issue.get('title', '(geen titel)')}",
        f"State: {issue.get('state', '?')}",
        f"Type: {'Pull request' if 'pull_request' in issue else 'Issue'}",
    ]
    if labels:
        lines.append(f"Labels: {', '.join(labels)}")
    if issue.get("created_at"):
        lines.append(f"Aangemaakt: {issue['created_at']}")
    if issue.get("closed_at"):
        lines.append(f"Gesloten: {issue['closed_at']}")
    body = (issue.get("body") or "").strip()
    if body:
        lines += ["", "Issue body:", body[:3000]]
    lines.append("")

    if closing and diff:
        lines += [
            f"Closing commit: {closing['short_sha']} ({closing['date']}) — {closing['subject']}",
            f"Auteur: {closing['author_name']} <{closing['author_email']}>",
        ]
        if closing.get("body"):
            lines += ["Commit body:", closing["body"][:1000]]
        lines += ["", "Diff-stat:", diff["stat"], "", "Diff (tot 8KB):", diff["diff"]]
    elif refs:
        lines.append("Geen closing-commit gedetecteerd. Wel referencerende commits:")
        for r in refs[:5]:
            lines.append(f"  - {r['short_sha']} ({r['date']}) — {r['subject']}")
    else:
        lines.append("⚠ Géén commits gedetecteerd die deze issue refereren. Beoordeel of de bevinding via een andere route is opgelost in de huidige repo-staat — dat is op zichzelf een traceerbaarheidsgap.")

    if exclude:
        lines.append(f"⚠ Door auditor uitgesloten bestanden: {', '.join(sorted(exclude))}.")
    if way_of_working:
        lines += [
            "",
            "<team_way_of_working>",
            "Onderstaande markdown is door het AI-agent development team aangeleverd als maatwerk-kader. Gebruik dit om je oordeel te tunen op de specifieke conventies van dit team.",
            way_of_working.strip()[:6000],
            "</team_way_of_working>",
        ]
    lines += [
        "",
        "Huidige repo-staat (om te verifiëren of de bevinding nog leeft):",
        f"<repo>\n{build_repo_xml(exclude=exclude)}\n</repo>",
        "",
        "Beoordeel adequaatheid van de opvolging. Geef in 'evidence' bestand/regel/quote uit diff of repo. Antwoord UITSLUITEND met JSON.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claude Agent SDK
# ---------------------------------------------------------------------------


async def run_claude(prompt: str, model: Optional[str], system_prompt: Optional[str] = None) -> str:
    options = ClaudeAgentOptions(
        system_prompt=system_prompt or SYSTEM_PROMPT_EVAL,
        model=model or "claude-sonnet-4-6",
        allowed_tools=[],
        max_turns=1,
        permission_mode="bypassPermissions",
    )
    collected: list[str] = []
    final_result: Optional[str] = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    collected.append(block.text)
        elif isinstance(message, ResultMessage):
            final_result = getattr(message, "result", None)
            if getattr(message, "is_error", False):
                raise RuntimeError(f"Claude Agent SDK gaf een fout terug: {final_result}")
    text = final_result if final_result else "".join(collected)
    if not text:
        raise RuntimeError("Lege respons van Claude Agent SDK")
    return text


async def analyze_orphan(commit: dict, model: Optional[str]) -> dict:
    owner, repo = TARGET["owner"], TARGET["repo"]
    if owner and repo:
        try:
            diff = await gh_get_commit_detail(owner, repo, commit["sha"])
        except Exception:
            diff = {"stat": "", "diff": ""}
    else:
        diff = {"stat": "", "diff": ""}
    prompt = "\n".join([
        f"Commit {commit['short_sha']} ({commit['date']}) — {commit['author_name']}",
        f"Subject: {commit['subject']}",
        f"Body: {commit.get('body', '') or '(leeg)'}",
        "",
        "Diff-stat:",
        diff["stat"] or "(geen)",
        "",
        "Beoordeel of deze commit via een issue had moeten lopen. Antwoord UITSLUITEND met JSON.",
    ])
    try:
        raw = await run_claude(prompt, model, system_prompt=SYSTEM_PROMPT_ORPHAN)
        data = extract_json(raw)
        v = data.get("verdict")
        if v not in ("needs_issue", "acceptable", "unclear"):
            v = "unclear"
        return {"verdict": v, "reasoning": data.get("reasoning") or ""}
    except Exception as e:
        return {"verdict": "unclear", "reasoning": f"Analyse mislukt: {e}"}


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="Agent Auditor", version=TOOL_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class EvalRequest(BaseModel):
    ac_code: str = Field(..., description="bv. AC-1.1")
    objective_id: str
    objective_title: str
    objective_statement: str
    framework: str
    framework_brief: str
    criterion_text: str
    extra_context: Optional[str] = None
    model: Optional[str] = "claude-sonnet-4-6"
    exclude_files: list[str] = Field(default_factory=list)
    way_of_working: Optional[str] = Field(None, description="Optionele markdown met team-WoW als maatwerk-kader (F-2)")


class EvalResponse(BaseModel):
    verdict: str
    reasoning: str
    evidence: list[dict]
    provenance: Optional[dict] = None
    integrity: Optional[dict] = None
    evidence_summary: Optional[dict] = None
    verdict_degraded: bool = False


class ConfigureTargetRequest(BaseModel):
    owner: Optional[str] = None
    repo: Optional[str] = None
    url: Optional[str] = None    # mag als alternatief voor owner/repo
    ref: Optional[str] = None    # branch, tag of (short) SHA
    files: Optional[list[str]] = None  # explicit list overrides auto-discover


class ListCommitsRequest(BaseModel):
    owner: Optional[str] = None
    repo: Optional[str] = None
    ref: Optional[str] = None
    limit: int = 30


class AuditTrailRequest(BaseModel):
    limit: int = 100
    model: Optional[str] = "claude-sonnet-4-6"
    force: bool = False
    exclude_files: list[str] = Field(default_factory=list)
    way_of_working: Optional[str] = Field(None, description="Optionele markdown met team-WoW als maatwerk-kader (F-2)")


class LogEntryRequest(BaseModel):
    type: str
    payload: dict


class AddOrgRequest(BaseModel):
    owner: str
    classify: bool = True
    model: Optional[str] = "claude-sonnet-4-6"


class RepoTagRequest(BaseModel):
    is_agent: Optional[bool] = None  # None = onbekend/auto, True/False = manual
    source: str = "manual"           # "manual" of "auto"
    reasoning: Optional[str] = None


class ACSummaryRequest(BaseModel):
    """A2 acceptance-criteria scoring vanuit de criteria-sheet."""
    verdicts: dict = Field(default_factory=dict, description="{AC-code: pass|fail|na|null}")
    pass_: int = Field(0, alias="pass")
    fail: int = 0
    na: int = 0
    open_: int = Field(0, alias="open")
    total: int = 0
    pct: Optional[int] = None
    verdict: str = ""
    accepted_ai_count: int = 0
    generated_at: Optional[str] = None
    model: Optional[str] = None
    tool_version: Optional[str] = None

    model_config = {"populate_by_name": True}


class AuditBranchRequest(BaseModel):
    reviewer: str = Field(..., description="naam — wordt slugified naar branchnaam")
    from_ref: Optional[str] = None   # leeg = default branch
    findings: list[str] = Field(default_factory=list, description="lijst van vrije-tekst-bevindingen; elke wordt door Claude opgepakt")
    model: Optional[str] = "claude-sonnet-4-6"
    generate_fixes: bool = True       # ook AUDIT_FIXES.md aanmaken


def _ensure_target() -> None:
    if not TARGET["configured"]:
        raise HTTPException(
            400,
            "Geen target geconfigureerd. POST eerst /configure-target met "
            "owner/repo (of url) en optioneel ref.",
        )


@app.get("/ping")
async def ping():
    routes = sorted({r.path for r in app.routes if hasattr(r, "path")})
    return {
        "ok": True,
        "tool": "claude-agent-sdk",
        "version": TOOL_VERSION,
        "build": SERVER_BUILD,
        "routes": routes,
        "target": TARGET,
        "files_loaded": list(REPO_CACHE.keys()),
        "provenance": current_provenance(),
        "integrity": {
            "bundle_hash": BUNDLE_HASH,
            "file_hashes": FILE_HASHES,
            "prompt_hash_eval": PROMPT_HASH_EVAL,
            "prompt_hash_audit": PROMPT_HASH_AUDIT,
            "prompt_hash_orphan": PROMPT_HASH_ORPHAN,
        },
    }


@app.post("/configure-target")
async def configure_target(req: ConfigureTargetRequest):
    owner, repo = req.owner, req.repo
    if req.url and not (owner and repo):
        parsed = parse_github_remote(req.url)
        if not parsed:
            raise HTTPException(400, "Kan owner/repo niet uit url afleiden.")
        owner, repo = parsed
    if not (owner and repo):
        raise HTTPException(400, "Specificeer owner+repo of url.")
    try:
        await load_target(owner, repo, req.ref, req.files)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    secret_findings = scan_bundle_for_secrets(REPO_CACHE)
    log_event("configure_target", {
        "owner": owner, "repo": repo, "ref": req.ref, "sha": TARGET["sha"],
        "secrets_high": sum(1 for s in secret_findings if s["severity"] == "high"),
        "secrets_total": len(secret_findings),
    })
    return {
        "ok": True,
        "target": TARGET,
        "provenance": current_provenance(),
        "integrity": {"bundle_hash": BUNDLE_HASH, "file_hashes": FILE_HASHES},
        "secret_findings": secret_findings,
    }


@app.post("/scan-secrets")
async def scan_secrets():
    """Voer alleen de secrets-scan opnieuw uit (bv. na file-uitsluiting)."""
    _ensure_target()
    findings = scan_bundle_for_secrets(REPO_CACHE)
    return {"secret_findings": findings, "commit": TARGET["sha"]}


@app.post("/list-commits")
async def list_commits(req: ListCommitsRequest):
    owner = req.owner or TARGET.get("owner")
    repo = req.repo or TARGET.get("repo")
    if not (owner and repo):
        raise HTTPException(400, "Specificeer owner+repo of configureer eerst een target.")
    ref = req.ref
    if not ref:
        ref = await gh_list_default_branch(owner, repo)
    try:
        commits = await gh_list_commits(owner, repo, ref, req.limit)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {"owner": owner, "repo": repo, "ref": ref, "commits": commits}


@app.post("/reload")
async def reload_target():
    if not TARGET["configured"]:
        raise HTTPException(400, "Geen target om te herladen.")
    await load_target(TARGET["owner"], TARGET["repo"], TARGET["ref_input"], None)
    return {
        "ok": True,
        "target": TARGET,
        "provenance": current_provenance(),
        "integrity": {"bundle_hash": BUNDLE_HASH, "file_hashes": FILE_HASHES},
    }


@app.post("/evaluate", response_model=EvalResponse)
async def evaluate(req: EvalRequest):
    _ensure_target()
    log_event("eval_request", {"ac_code": req.ac_code, "model": req.model, "objective_id": req.objective_id})
    prompt = build_user_message(req)
    try:
        raw_text = await run_claude(prompt, req.model)
    except Exception as e:
        raise HTTPException(502, f"Claude Agent SDK fout: {e}")
    try:
        data = extract_json(raw_text)
    except Exception as e:
        raise HTTPException(500, f"Kon AI-antwoord niet als JSON parsen ({e}). Raw: {raw_text[:300]}")

    verdict = data.get("verdict", "unknown")
    if verdict not in ("pass", "fail", "na", "unknown"):
        verdict = "unknown"

    validated_evidence, evidence_summary = validate_evidence(data.get("evidence", []) or [])
    verdict_degraded = False
    reasoning_text = data.get("reasoning", "") or ""
    if evidence_summary["all_hallucinated"] and verdict in ("pass", "fail"):
        verdict = "unknown"
        verdict_degraded = True
        reasoning_text = (
            "[verdict gedegradeerd naar 'unknown' — alle door Claude opgegeven "
            "evidence-quotes konden niet in de bundle worden gevonden] "
            + reasoning_text
        )

    log_event("eval_response", {
        "ac_code": req.ac_code,
        "verdict": verdict,
        "verdict_degraded": verdict_degraded,
        "evidence_summary": evidence_summary,
    })

    prov = current_provenance()
    return EvalResponse(
        verdict=verdict,
        reasoning=reasoning_text,
        evidence=validated_evidence,
        provenance={
            "commit_short": prov["commit_short"],
            "commit": prov["commit"],
            "branch": prov["branch"],
            "dirty": prov["dirty"],
        },
        integrity={
            "tool_version": TOOL_VERSION,
            "prompt_hash": PROMPT_HASH_EVAL,
            "bundle_hash": effective_bundle_hash(set(req.exclude_files or [])),
            "bundle_hash_full": BUNDLE_HASH,
            "excluded_files": sorted(req.exclude_files or []),
            "model": req.model,
            "wow_hash": _sha256(req.way_of_working or ""),
            "wow_applied": bool(req.way_of_working),
        },
        evidence_summary=evidence_summary,
        verdict_degraded=verdict_degraded,
    )


@app.post("/audit-trail")
async def audit_trail(req: AuditTrailRequest):
    _ensure_target()
    excl = set(req.exclude_files or [])
    eff_bundle = effective_bundle_hash(excl)
    wow_hash = _sha256(req.way_of_working or "")

    if not req.force and AUDIT_CACHE_FILE.exists():
        try:
            cached = json.loads(AUDIT_CACHE_FILE.read_text(encoding="utf-8"))
            cached_integ = cached.get("integrity") or {}
            same_commit = cached.get("commit_at_cache") == TARGET["sha"]
            same_model = cached.get("model") == req.model
            same_prompt = cached_integ.get("prompt_hash_audit") == PROMPT_HASH_AUDIT
            same_bundle = cached_integ.get("bundle_hash") == eff_bundle
            same_excl = set(cached.get("exclude_files") or []) == excl
            same_wow = cached_integ.get("wow_hash") == wow_hash
            if same_commit and same_model and same_prompt and same_bundle and same_excl and same_wow:
                cached["from_cache"] = True
                return cached
        except Exception:
            pass

    owner = TARGET["owner"]
    repo = TARGET["repo"]
    commits = await gh_list_commits(owner, repo, TARGET["sha"], req.limit)

    issue_to_commits: dict[int, list[dict]] = {}
    issue_to_closing: dict[int, dict] = {}
    orphan_commits: list[dict] = []
    for c in commits:
        text = f"{c['subject']}\n{c.get('body','')}"
        all_refs = {int(m.group(1)) for m in ISSUE_REF_RE.finditer(text)}
        closing_refs = {int(m.group(2)) for m in CLOSING_RE.finditer(text)}
        if not all_refs:
            orphan_commits.append(c)
        for num in all_refs:
            issue_to_commits.setdefault(num, []).append(c)
        for num in closing_refs:
            if num not in issue_to_closing:
                issue_to_closing[num] = c

    log.info("Audit-trail %s/%s: %d commits, %d issues gerefereerd, %d orphan", owner, repo, len(commits), len(issue_to_commits), len(orphan_commits))

    try:
        gh_issues = await gh_get(f"/repos/{owner}/{repo}/issues?state=all&per_page=100")
    except Exception as e:
        raise HTTPException(502, f"GitHub-fetch mislukt: {e}")
    if gh_issues is None:
        raise HTTPException(404, f"Repo {owner}/{repo} niet vindbaar via GitHub API.")
    issues_by_num: dict[int, dict] = {i["number"]: i for i in gh_issues}
    for num in issue_to_commits:
        if num not in issues_by_num:
            try:
                fetched = await gh_get(f"/repos/{owner}/{repo}/issues/{num}")
                if fetched:
                    issues_by_num[num] = fetched
            except Exception:
                pass

    items = []
    for num in sorted(issues_by_num.keys()):
        issue = issues_by_num[num]
        closing = issue_to_closing.get(num)
        refs = issue_to_commits.get(num, [])
        diff = await gh_get_commit_detail(owner, repo, closing["sha"]) if closing else None

        try:
            prompt = build_audit_prompt(issue, closing, diff, refs, exclude=excl, way_of_working=req.way_of_working)
            raw = await run_claude(prompt, req.model, system_prompt=SYSTEM_PROMPT_AUDIT)
            analysis = extract_json(raw)
        except Exception as e:
            log.exception("Audit-analyse fout voor #%s", num)
            analysis = {
                "verdict": "open" if not closing else "inadequate",
                "reasoning": f"AI-analyse mislukt: {e}",
                "evidence": [],
                "follow_up_required": ["Handmatig beoordelen — AI-analyse faalde"],
            }

        verdict = analysis.get("verdict")
        if verdict not in ("adequate", "partial", "inadequate", "open", "unrelated"):
            verdict = "open" if not closing else "inadequate"
        analysis["verdict"] = verdict

        validated_ev, ev_summary = validate_evidence(analysis.get("evidence", []) or [])
        analysis["evidence"] = validated_ev
        analysis["evidence_summary"] = ev_summary
        if ev_summary["all_hallucinated"] and verdict in ("adequate", "partial"):
            analysis["verdict"] = "inadequate"
            analysis["verdict_degraded"] = True
            analysis["reasoning"] = "[gedegradeerd — geen verifieerbare evidence] " + (analysis.get("reasoning") or "")

        items.append({
            "number": num,
            "title": issue.get("title", ""),
            "state": issue.get("state", ""),
            "url": issue.get("html_url", ""),
            "labels": [l["name"] for l in issue.get("labels", []) if isinstance(l, dict)],
            "is_pr": "pull_request" in issue,
            "body_excerpt": (issue.get("body") or "").strip()[:1500],
            "author": (issue.get("user") or {}).get("login", ""),
            "created_at": issue.get("created_at", ""),
            "closed_at": issue.get("closed_at"),
            "closing_commit": closing,
            "referencing_commits": [
                {"short_sha": r["short_sha"], "subject": r["subject"], "date": r["date"]}
                for r in refs
            ],
            "diff_stat": diff["stat"] if diff else None,
            "analysis": analysis,
        })

    verdicts_counter: dict[str, int] = {}
    for it in items:
        v = it["analysis"]["verdict"]
        verdicts_counter[v] = verdicts_counter.get(v, 0) + 1

    # P-7 orphan-AI-pass (cap 15)
    orphan_analyses = []
    for c in orphan_commits[:15]:
        a = await analyze_orphan(c, req.model)
        orphan_analyses.append({
            "short_sha": c["short_sha"],
            "subject": c["subject"],
            "date": c["date"],
            "author": c["author_name"],
            "verdict": a["verdict"],
            "reasoning": a["reasoning"],
        })
    orphan_verdicts = {v: sum(1 for o in orphan_analyses if o["verdict"] == v)
                       for v in ("needs_issue", "acceptable", "unclear")}

    result = {
        "commit_at_cache": TARGET["sha"],
        "model": req.model,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "owner": owner,
        "repo": repo,
        "exclude_files": sorted(excl),
        "integrity": {
            "tool_version": TOOL_VERSION,
            "prompt_hash_audit": PROMPT_HASH_AUDIT,
            "prompt_hash_orphan": PROMPT_HASH_ORPHAN,
            "bundle_hash": eff_bundle,
            "bundle_hash_full": BUNDLE_HASH,
            "file_hashes": FILE_HASHES,
            "wow_hash": wow_hash,
            "wow_applied": bool(req.way_of_working),
        },
        "summary": {
            "commits_walked": len(commits),
            "issues_total": len(items),
            "issues_closed_via_commit": sum(1 for i in items if i["closing_commit"]),
            "open_issues": sum(1 for i in items if i["state"] == "open"),
            "orphan_commits": len(orphan_commits),
            "verdicts": verdicts_counter,
            "orphan_verdicts": orphan_verdicts,
        },
        "items": items,
        "orphan_commits": [
            {"short_sha": c["short_sha"], "date": c["date"], "subject": c["subject"], "author": c["author_name"]}
            for c in orphan_commits[:30]
        ],
        "orphan_analyses": orphan_analyses,
        "secret_findings": scan_bundle_for_secrets(REPO_CACHE),
        "from_cache": False,
    }
    try:
        AUDIT_CACHE_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as e:
        log.warning("Kon audit-trail.cache.json niet schrijven: %s", e)

    # D-4: dashboard metrics bijwerken met de AI-verdicts uit deze volledige run
    try:
        state = load_orgs()
        org_state = find_org(state, owner)
        if org_state:
            repo_state = find_repo(org_state, repo)
            if repo_state:
                v = result["summary"]["verdicts"]
                ov = result["summary"].get("orphan_verdicts", {})
                sf = result.get("secret_findings", [])
                existing = repo_state.get("metrics") or {}
                merged = {
                    "last_audit_at": result["generated_at"],
                    "commit": result["commit_at_cache"],
                    "commit_short": (result["commit_at_cache"] or "")[:7],
                    "issues_total": result["summary"]["issues_total"],
                    "issues_open": result["summary"]["open_issues"],
                    "issues_closed": result["summary"]["issues_total"] - result["summary"]["open_issues"],
                    "closed_with_commit": result["summary"]["issues_closed_via_commit"],
                    "orphan_commits": result["summary"]["orphan_commits"],
                    "orphan_needs_issue": ov.get("needs_issue", 0),
                    "adequate": v.get("adequate", 0),
                    "partial": v.get("partial", 0),
                    "inadequate": v.get("inadequate", 0),
                    "open_findings": v.get("open", 0),
                    "secrets_total": len(sf),
                    "secrets_high": sum(1 for s in sf if s["severity"] == "high" and not s["is_example"]),
                    "secrets_medium": sum(1 for s in sf if s["severity"] == "medium" and not s["is_example"]),
                    "scan_type": "full",
                    "model": req.model,
                }
                # Behoud ac_summary + ac_verdicts uit criteria-sheet
                for k in ("ac_summary", "ac_verdicts"):
                    if k in existing:
                        merged[k] = existing[k]
                repo_state["metrics"] = merged
                save_orgs(state)
    except Exception as e:
        log.warning("Kon dashboard metrics niet updaten na audit-trail: %s", e)

    log_event("audit_trail_run", {"owner": owner, "repo": repo, "summary": result["summary"], "model": req.model})
    return result


@app.post("/log")
async def append_log(req: LogEntryRequest):
    allowed = {"accept_suggestion", "reject_suggestion", "dismiss_suggestion",
               "manual_score", "manual_unset", "audit_session_open",
               "audit_session_reset", "export_pdf", "configure_target"}
    if req.type not in allowed:
        raise HTTPException(400, f"Onbekend event-type: {req.type}.")
    log_event(req.type, req.payload or {})
    return {"ok": True}


@app.get("/log")
async def read_log(limit: int = 200):
    if not ACTIONS_LOG.exists():
        return {"entries": [], "total": 0}
    try:
        lines = ACTIONS_LOG.read_text(encoding="utf-8").strip().splitlines()
        total = len(lines)
        tail = lines[-limit:] if limit > 0 else lines
        entries = []
        for line in tail:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return {"entries": entries, "total": total}
    except Exception as e:
        raise HTTPException(500, f"Kon log niet lezen: {e}")


# ---------------------------------------------------------------------------
# D-1: Multi-org dashboard endpoints
# ---------------------------------------------------------------------------


@app.get("/orgs")
async def list_orgs():
    return load_orgs()


@app.post("/orgs")
async def add_org(req: AddOrgRequest):
    state = load_orgs()
    owner = req.owner.strip().strip("/").split("/")[-1] if "/" in req.owner else req.owner.strip()
    if not owner:
        raise HTTPException(400, "Specificeer owner (bv. SAAF-Project of een github.com/X URL).")
    repos = await gh_list_org_repos(owner)
    if not repos:
        raise HTTPException(404, f"Geen repos gevonden voor {owner} (privé zonder token?).")

    existing = find_org(state, owner)
    if existing is None:
        existing = {
            "owner": owner,
            "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "last_scan": None,
            "repos": [],
        }
        state["orgs"].append(existing)

    # Repos mergen — bestaande tags niet overschrijven
    by_name = {r["name"]: r for r in existing["repos"]}
    for gh_repo in repos:
        prev = by_name.get(gh_repo["name"])
        if prev:
            prev["default_branch"] = gh_repo["default_branch"]
            prev["description"] = gh_repo["description"]
            prev["private"] = gh_repo["private"]
            prev["archived"] = gh_repo["archived"]
            prev["stars"] = gh_repo["stars"]
        else:
            existing["repos"].append({
                **gh_repo,
                "is_agent": None,
                "tag_source": None,
                "agent_classification": None,
                "metrics": None,
            })

    # Optionele classificatie — sequentieel om rate-limit te respecteren
    if req.classify:
        log.info("Classificeer %d repos van %s …", len(repos), owner)
        for r in existing["repos"]:
            if r.get("tag_source") == "manual":
                continue  # respecteer handmatige tags
            if r.get("archived"):
                continue
            classification = await classify_agent(owner, r["name"], req.model)
            r["agent_classification"] = classification
            r["is_agent"] = (classification["verdict"] == "agent")
            r["tag_source"] = "auto"

    existing["last_scan"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_orgs(state)
    log_event("add_org", {"owner": owner, "n_repos": len(repos), "classified": req.classify})
    return {"ok": True, "org": existing, "n_classified": sum(1 for r in existing["repos"] if r.get("agent_classification"))}


@app.delete("/orgs/{owner}")
async def remove_org(owner: str):
    state = load_orgs()
    state["orgs"] = [o for o in state["orgs"] if o["owner"].lower() != owner.lower()]
    save_orgs(state)
    return {"ok": True}


@app.post("/orgs/{owner}/rescan")
async def rescan_org(owner: str, model: Optional[str] = "claude-sonnet-4-6"):
    """Herhaal de README-classificatie voor alle non-manual repos."""
    state = load_orgs()
    org = find_org(state, owner)
    if not org:
        raise HTTPException(404, f"Org {owner} niet bekend.")
    n = 0
    for r in org["repos"]:
        if r.get("tag_source") == "manual" or r.get("archived"):
            continue
        c = await classify_agent(owner, r["name"], model)
        r["agent_classification"] = c
        r["is_agent"] = (c["verdict"] == "agent")
        r["tag_source"] = "auto"
        n += 1
    org["last_scan"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_orgs(state)
    return {"ok": True, "rescanned": n, "org": org}


@app.post("/repos/{owner}/{repo}/tag")
async def tag_repo(owner: str, repo: str, req: RepoTagRequest):
    """Handmatig de agent-tag aan/uit/clear zetten op een specifieke repo."""
    state = load_orgs()
    org = find_org(state, owner)
    if not org:
        raise HTTPException(404, f"Org {owner} niet bekend.")
    r = find_repo(org, repo)
    if not r:
        raise HTTPException(404, f"Repo {owner}/{repo} niet bekend.")
    r["is_agent"] = req.is_agent
    r["tag_source"] = req.source or "manual"
    if req.reasoning:
        r.setdefault("manual_notes", []).append({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "is_agent": req.is_agent,
            "reasoning": req.reasoning,
        })
    save_orgs(state)
    log_event("repo_tag", {"owner": owner, "repo": repo, "is_agent": req.is_agent, "source": req.source})
    return {"ok": True, "repo": r}


# ---------------------------------------------------------------------------
# D-4: light metrics scan voor dashboard (geen Claude-call per issue)
# ---------------------------------------------------------------------------


async def compute_repo_metrics(owner: str, repo: str) -> dict:
    """Lichte scan: counts uit GitHub + secrets-scan + orphan-count.
    De zware /audit-trail (AI per issue) blijft beschikbaar voor drill-down."""
    default_branch = await gh_list_default_branch(owner, repo)
    head = await gh_resolve_ref(owner, repo, default_branch)
    sha = head["sha"]

    # Issues (excl. PRs)
    issues_raw = await gh_get(f"/repos/{owner}/{repo}/issues?state=all&per_page=100") or []
    issues = [i for i in issues_raw if isinstance(i, dict) and "pull_request" not in i]
    n_open = sum(1 for i in issues if i.get("state") == "open")
    n_closed = sum(1 for i in issues if i.get("state") == "closed")

    # Commits + orphans + closed-by-commit
    commits = await gh_list_commits(owner, repo, sha, 50)
    orphan_count = 0
    closed_with_commit: set[int] = set()
    for c in commits:
        text = f"{c['subject']}\n{c.get('body','')}"
        all_refs = {int(m.group(1)) for m in ISSUE_REF_RE.finditer(text)}
        closing_refs = {int(m.group(2)) for m in CLOSING_RE.finditer(text)}
        if not all_refs:
            orphan_count += 1
        for num in closing_refs:
            closed_with_commit.add(num)

    # Bundle ophalen voor secrets-scan (geïsoleerd; niet in globale REPO_CACHE)
    tree_files = await discover_files(owner, repo, sha)
    bundle: dict[str, str] = {}
    total = 0
    for entry in tree_files[:15]:
        content = await gh_get_file(owner, repo, entry["path"], sha)
        if content is None:
            continue
        if total + len(content) > 150_000:
            break
        bundle[entry["path"]] = content
        total += len(content)
    secrets = scan_bundle_for_secrets(bundle)
    sec_high = sum(1 for s in secrets if s["severity"] == "high" and not s["is_example"])
    sec_med = sum(1 for s in secrets if s["severity"] == "medium" and not s["is_example"])

    return {
        "last_audit_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": sha,
        "commit_short": sha[:7],
        "default_branch": default_branch,
        "issues_total": n_open + n_closed,
        "issues_open": n_open,
        "issues_closed": n_closed,
        "closed_with_commit": len(closed_with_commit),
        "orphan_commits": orphan_count,
        "orphan_needs_issue": 0,           # alleen gevuld na full audit
        "adequate": 0,
        "partial": 0,
        "inadequate": 0,
        "open_findings": n_open,
        "secrets_total": len(secrets),
        "secrets_high": sec_high,
        "secrets_medium": sec_med,
        "scan_type": "light",
    }


@app.post("/repos/{owner}/{repo}/audit")
async def audit_repo_light(owner: str, repo: str):
    """Light scan voor dashboard — geen Claude-call per issue, alleen
    counts + secrets. Volledige adequaatheid-analyse via drill-down."""
    state = load_orgs()
    org = find_org(state, owner)
    if not org:
        raise HTTPException(404, f"Org {owner} niet bekend — voeg eerst toe.")
    r = find_repo(org, repo)
    if not r:
        raise HTTPException(404, f"Repo {owner}/{repo} niet bekend in dashboard-state.")
    try:
        metrics = await compute_repo_metrics(owner, repo)
    except Exception as e:
        log.exception("compute_repo_metrics fout")
        raise HTTPException(502, str(e))
    # Merge: behoud ac_summary + ac_verdicts uit eerdere criteria-sheet runs
    existing = r.get("metrics") or {}
    for k in ("ac_summary", "ac_verdicts"):
        if k in existing:
            metrics[k] = existing[k]
    r["metrics"] = metrics
    save_orgs(state)
    log_event("repo_audit_light", {"owner": owner, "repo": repo, "metrics": metrics})
    return {"ok": True, "metrics": metrics, "repo": r}


@app.post("/repos/{owner}/{repo}/ac-summary")
async def update_ac_summary(owner: str, repo: str, req: ACSummaryRequest):
    """De criteria-sheet pusht z'n actuele AC-tellingen + verdicts hierheen
    zodat het dashboard de echte A2-score laat zien i.p.v. de light-scan
    heuristiek. Wordt typisch gedebounced aangeroepen na elke verdict-wijziging."""
    state = load_orgs()
    org = find_org(state, owner)
    if not org:
        raise HTTPException(404, f"Org {owner} niet bekend.")
    r = find_repo(org, repo)
    if not r:
        raise HTTPException(404, f"Repo {owner}/{repo} niet bekend in dashboard-state.")
    metrics = r.get("metrics") or {}
    metrics["ac_summary"] = {
        "pass": req.pass_,
        "fail": req.fail,
        "na": req.na,
        "open": req.open_,
        "total": req.total,
        "pct": req.pct,
        "verdict": req.verdict,
        "accepted_ai_count": req.accepted_ai_count,
        "generated_at": req.generated_at,
        "model": req.model,
        "tool_version": req.tool_version,
    }
    metrics["ac_verdicts"] = req.verdicts
    r["metrics"] = metrics
    save_orgs(state)
    log_event("ac_summary_update", {
        "owner": owner, "repo": repo,
        "pass": req.pass_, "fail": req.fail, "open": req.open_, "total": req.total,
        "pct": req.pct, "verdict": req.verdict,
    })
    return {"ok": True, "metrics": metrics}


# ---------------------------------------------------------------------------
# D-5: audit-branch (op same repo, geen GitHub-fork)
# ---------------------------------------------------------------------------


@app.post("/repos/{owner}/{repo}/audit-branch")
async def create_audit_branch(owner: str, repo: str, req: AuditBranchRequest):
    """Maak een branch 'auditedby_<reviewer>_<datum>' op dezelfde repo,
    optioneel direct AUDIT_FIXES.md met Claude-fix-voorstellen.
    De main-branch blijft van het dev-team; deze branch is van de auditor."""
    if not req.reviewer or not req.reviewer.strip():
        raise HTTPException(400, "Reviewer-naam is verplicht voor branch-naam.")

    # Resolve from_ref
    from_ref = req.from_ref or await gh_list_default_branch(owner, repo)
    base = await gh_resolve_ref(owner, repo, from_ref)
    base_sha = base["sha"]

    branch = make_audit_branch_name(req.reviewer)
    log.info("Audit-branch %s op %s/%s vanaf %s", branch, owner, repo, base_sha[:7])

    try:
        ref = await gh_create_branch(owner, repo, branch, base_sha)
    except RuntimeError as e:
        msg = str(e)
        # 422 typisch = ref bestaat al; we hergebruiken hem
        if "422" in msg or "exists" in msg.lower():
            log.info("Branch %s bestaat al — hergebruik", branch)
            ref = {"ref": f"refs/heads/{branch}", "object": {"sha": base_sha}}
        else:
            raise HTTPException(502, msg)

    result = {
        "ok": True,
        "branch": branch,
        "from_ref": from_ref,
        "base_sha": base_sha,
        "url": f"https://github.com/{owner}/{repo}/tree/{branch}",
        "fixes_committed": False,
        "fixes_url": None,
        "proposals": [],
    }

    # Optioneel: per bevinding een fix-voorstel + één gecombineerde AUDIT_FIXES.md
    if req.generate_fixes and req.findings:
        log.info("Genereer %d fix-voorstellen voor branch %s", len(req.findings), branch)
        proposals: list[dict] = []
        for idx, f in enumerate(req.findings, 1):
            p = await propose_fix(f, req.model)
            proposals.append({"finding": f, **p, "index": idx})
        md = _render_fixes_markdown(owner, repo, branch, req.reviewer, proposals)
        try:
            commit = await gh_put_file(
                owner, repo, branch, "AUDIT_FIXES.md", md,
                f"audit: fix-voorstellen door Claude voor {req.reviewer}",
            )
            result["fixes_committed"] = True
            result["fixes_url"] = f"https://github.com/{owner}/{repo}/blob/{branch}/AUDIT_FIXES.md"
            result["fixes_commit_sha"] = commit.get("commit", {}).get("sha")
        except RuntimeError as e:
            result["fixes_error"] = str(e)
        result["proposals"] = proposals

    log_event("audit_branch_created", {
        "owner": owner, "repo": repo, "branch": branch,
        "reviewer": req.reviewer, "n_proposals": len(result["proposals"]),
    })
    return result


def _render_fixes_markdown(owner: str, repo: str, branch: str, reviewer: str, proposals: list[dict]) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        f"# Audit Fixes — voorgesteld door Claude",
        "",
        f"> **Repo:** `{owner}/{repo}`  ",
        f"> **Branch:** `{branch}`  ",
        f"> **Reviewer:** {reviewer}  ",
        f"> **Gegenereerd:** {ts}  ",
        f"> **Tool:** Agent Auditor v{TOOL_VERSION}",
        "",
        "Deze fixes zijn door Claude voorgesteld op basis van de auditbevindingen — review en pas aan vóór je merged. Dit bestand is een voorstel, geen vaststaande wijziging.",
        "",
        "---",
        "",
    ]
    for p in proposals:
        files = ", ".join(f"`{f}`" for f in p.get("files_likely_affected") or []) or "—"
        lines += [
            f"## Fix #{p['index']}: {p.get('title', '(geen titel)')}",
            "",
            f"**Source finding:** {p['finding']}",
            "",
            f"**Root cause:** {p.get('root_cause', '—')}",
            "",
            f"**Voorgestelde wijziging:** {p.get('proposed_change', '—')}",
            "",
            f"**Bestanden vermoedelijk betrokken:** {files}",
            "",
            f"**Verificatie:** {p.get('verification', '—')}",
            "",
            f"**Complexiteit:** `{p.get('complexity', 'moderate')}`",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


@app.post("/repos/{owner}/{repo}/classify")
async def classify_single_repo(owner: str, repo: str, model: Optional[str] = "claude-sonnet-4-6"):
    """Heen herclassificatie op één enkele repo (handig voor 'Re-classify' knop)."""
    state = load_orgs()
    org = find_org(state, owner)
    if not org:
        raise HTTPException(404, f"Org {owner} niet bekend.")
    r = find_repo(org, repo)
    if not r:
        raise HTTPException(404, f"Repo {owner}/{repo} niet bekend.")
    c = await classify_agent(owner, repo, model)
    r["agent_classification"] = c
    if r.get("tag_source") != "manual":
        r["is_agent"] = (c["verdict"] == "agent")
        r["tag_source"] = "auto"
    save_orgs(state)
    return {"ok": True, "repo": r}


if __name__ == "__main__":
    import uvicorn

    log.info("Agent Auditor v%s (build %s)", TOOL_VERSION, SERVER_BUILD)
    log.info("Start zonder geconfigureerd target. Gebruik POST /configure-target uit de webapp.")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
