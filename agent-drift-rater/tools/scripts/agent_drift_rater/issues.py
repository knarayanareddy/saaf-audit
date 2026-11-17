"""Turn approved fix suggestions into GitHub issue drafts for the analyzed repository.

The reviewer approves suggestions in the dashboard; this module renders each approved
suggestion as an issue (title + body) targeting the repo that was analyzed, and the CLI files
them with `gh`. Bodies cite the agent, its rating and the fix — never verbatim code. Creation
is opt-in (dry-run by default) and whitelisted per repo, so nothing is posted by accident.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TITLE_MAX = 80
ISSUE_LABEL = "agent-drift"


@dataclass
class IssueDraft:
    repo: str            # bare repo name within the org
    unit_id: str
    title: str
    body: str


def _trim(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def parse_approved(raw: Any) -> List[str]:
    """Accept a JSON array of fix ids ('unit__idx') or of {unit, index} objects."""
    if isinstance(raw, dict):
        raw = raw.get("fixes") or raw.get("approved") or []
    ids: List[str] = []
    for item in raw or []:
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict) and "unit" in item and "index" in item:
            ids.append(f"{item['unit']}__{item['index']}")
    return ids


def _split_fix_id(fix_id: str) -> Optional[Tuple[str, int]]:
    marker = fix_id.rfind("__")
    if marker == -1:
        return None
    unit, idx = fix_id[:marker], fix_id[marker + 2:]
    if not idx.isdigit():
        return None
    return unit, int(idx)


def build_issue(unit: Dict[str, Any], advice_index: int, run_id: str) -> Optional[IssueDraft]:
    advice = unit.get("advice") or []
    if advice_index >= len(advice):
        return None
    a = advice[advice_index]
    r = unit["ratings"]
    raised = [f["rf"] for f in unit.get("red_flags", []) if f["status"] == "raised"]
    unit_path = unit.get("unit_path") or "/"
    what = a.get("what") or "Reduce drift risk"
    title = _trim(f"[agent-drift] {what}", TITLE_MAX)
    body = (
        f"**Agent drift review — fix request**\n\n"
        f"- **Agent:** `{unit['unit_id']}`  (path `{unit_path}`)\n"
        f"- **Residual drift rating:** {r['residual']}  ·  **Controls:** {r['control_strength']}\n"
        f"- **Red flags raised:** {', '.join(raised) if raised else 'none'}\n\n"
        f"**Suggested fix:** {a.get('what','')}\n\n"
        f"**Why:** {a.get('why','')}\n\n"
        f"**How:** {a.get('how','')}\n\n"
        f"---\n"
        f"_Filed from the SAAF Agent Drift Rater (run `{run_id}`), approved by the reviewer on "
        f"{date.today().isoformat()}. Static design review — design evidence, not certification; "
        f"cites file paths and line numbers only, never code._"
    )
    return IssueDraft(repo=unit.get("repo") or unit["unit_id"], unit_id=unit["unit_id"],
                      title=title, body=body)


def drafts_for(report: Dict[str, Any], fix_ids: List[str]) -> List[IssueDraft]:
    by_id = {u["unit_id"]: u for u in report["units"]}
    run_id = report["run"]["run_id"]
    drafts: List[IssueDraft] = []
    seen = set()
    for fid in fix_ids:
        split = _split_fix_id(fid)
        if not split:
            logger.warning("skipping malformed fix id: %s", fid)
            continue
        unit_id, idx = split
        unit = by_id.get(unit_id)
        if not unit:
            logger.warning("fix id names an unknown unit: %s", unit_id)
            continue
        draft = build_issue(unit, idx, run_id)
        if draft and (draft.repo, draft.title) not in seen:
            seen.add((draft.repo, draft.title))
            drafts.append(draft)
    return drafts


def existing_titles(org: str, repo: str) -> set:
    """Titles of open+closed issues in the repo (for de-duplication). Empty on any error."""
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--repo", f"{org}/{repo}", "--state", "all", "--limit", "200",
             "--json", "title"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=60, check=False)
        if out.returncode != 0:
            return set()
        return {row.get("title", "") for row in json.loads(out.stdout or "[]")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not list existing issues for %s/%s: %s", org, repo, exc)
        return set()


def create_issue(org: str, draft: IssueDraft, label: bool) -> Optional[str]:
    """Create the issue with gh; return its URL, or None on failure."""
    cmd = ["gh", "issue", "create", "--repo", f"{org}/{draft.repo}",
           "--title", draft.title, "--body", draft.body]
    if label:
        cmd += ["--label", ISSUE_LABEL]
    try:
        out = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace",
                             timeout=60, check=False)
        if out.returncode != 0:
            logger.error("gh issue create failed for %s/%s: %s", org, draft.repo,
                         (out.stderr or out.stdout).strip())
            return None
        return (out.stdout or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("gh issue create error for %s/%s: %s", org, draft.repo, exc)
        return None
