#!/usr/bin/env python3
"""Generate dashboard JSON data from SAAF plan Markdown files.

Reads all plan .md files, overview.md (quality scores), workstreams.md
(track assignments), and gap-analysis.md (domain coverage) and writes:
  - website/data/plans.json
  - website/data/tracks.json
  - website/data/gaps.json
  - website/data/submitters.json
  - website/data/progress.json (project -> temple part -> plan -> PDCA phase roll-up
    for the portal's progress visual: kind, stage, alerts, sector tags and plan -> repo links)

Curated inputs for progress.json live in plans/metadata/ (sectors.json, plan-repos.json).
"""

import datetime
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("generate_dashboard")

ROOT = Path(__file__).parents[2]
PLANS_DIR = ROOT / "plans"
META_DIR = PLANS_DIR / "metadata"
OUT_DIR = ROOT / "website" / "data"
GITHUB_BASE = "https://github.com/SAAF-Project/SAAF-Project/blob/main/plans"

PLAN_DIRS = [
    ("alignment", PLANS_DIR / "alignment"),
    ("hackathon-2", PLANS_DIR / "hackathon-2"),
    ("hackathon-3", PLANS_DIR / "hackathon-3"),
    ("hackathon-4", PLANS_DIR / "hackathon-4"),
]

TEMPLATE_TITLE = "Plan Template \u2014 SAAF Hackathon Submission"


def parse_metadata_table(text: str) -> dict:
    """Extract Section 1 metadata table fields."""
    meta = {}
    for m in re.finditer(r"\|\s*\*\*(\w[\w\s]*?)\*\*\s*\|\s*(.+?)\s*\|", text):
        key = m.group(1).strip().lower().replace(" ", "_")
        val = m.group(2).strip()
        val = val.rstrip("\\").strip()  # strip trailing backslash from escaped pipes
        # Handle escaped pipes in submitter field
        if "\\|" in val:
            val = val.split("\\|")[0].strip()
        meta[key] = val
    return meta


PDCA_SECTION_RE = re.compile(r"## \d+\.\s*PDCA.*?\n(.*?)(?=\n## |\Z)", re.DOTALL)


def classify_pdca_status(status_text: str) -> str:
    """Map a free-text PDCA status cell to complete / in_progress / not_started."""
    s = status_text.lower()
    if re.search(r"\bnot\s+(yet\s+)?complete", s):
        return "not_started"
    if re.search(r"\bcomplete\b", s):
        return "complete"
    if "in progress" in s or "in-progress" in s:
        return "in_progress"
    return "not_started"


def parse_pdca(text: str) -> dict:
    """Extract PDCA status from the PDCA section (any section number)."""
    pdca = {"plan": "not_started", "do": "not_started", "check": "not_started", "act": "not_started"}
    section_match = PDCA_SECTION_RE.search(text)
    if not section_match:
        return pdca
    section = section_match.group(1)
    for phase in ["plan", "do", "check", "act"]:
        pattern = rf"\*\*{phase.capitalize()}\*\*\s*\|\s*(.+?)\s*\|"
        m = re.search(pattern, section, re.IGNORECASE)
        if m:
            pdca[phase] = classify_pdca_status(m.group(1))
    return pdca


def has_pdca(text: str) -> bool:
    """True if the plan has a PDCA table with all four phases (else its progress is unknown)."""
    section_match = PDCA_SECTION_RE.search(text)
    if not section_match:
        return False
    section = section_match.group(1)
    return all(
        re.search(rf"\*\*{phase}\*\*\s*\|", section, re.IGNORECASE)
        for phase in ("Plan", "Do", "Check", "Act")
    )


def parse_problem_summary(text: str) -> str:
    """Extract first paragraph of Section 2."""
    m = re.search(r"## 2\.\s*Problem Statement\s*\n\n(.+?)(?:\n\n|\n-|\n\||\n#)", text, re.DOTALL)
    if m:
        summary = m.group(1).strip()
        summary = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", summary)  # strip markdown links
        return summary[:200] + ("..." if len(summary) > 200 else "")
    return ""


def parse_title(text: str) -> str:
    """Extract H1 title."""
    m = re.match(r"#\s+(.+)", text)
    return m.group(1).strip() if m else ""


def parse_overview_domains(overview_path: Path) -> dict:
    """Parse slug → Domain mapping from overview.md tables for use as title fallback."""
    domains = {}
    if not overview_path.exists():
        return domains
    text = overview_path.read_text()
    # Match table rows: | [`slug.md`](...) | Type | Submitter | Domain | ...
    for m in re.finditer(r"\|\s*\[`([^`]+\.md)`\][^|]*\|\s*[^|]+\|\s*[^|]+\|\s*([^|]+)\|", text):
        slug = m.group(1).replace(".md", "")
        domain = m.group(2).strip()
        if domain and domain not in ("Domain", "---"):
            domains[slug] = domain
    return domains


def parse_quality_scores(overview_path: Path) -> dict:
    """Parse quality scores from overview.md Score column."""
    scores = {}
    if not overview_path.exists():
        return scores
    text = overview_path.read_text()
    for m in re.finditer(r"\[`([^`]+\.md)`\].*?\|\s*(\d)\s*\|", text):
        slug = m.group(1).replace(".md", "")
        scores[slug] = int(m.group(2))
    return scores


def parse_track_assignments(workstreams_path: Path) -> dict:
    """Parse track assignments from the appendix table in workstreams.md."""
    assignments = {}
    if not workstreams_path.exists():
        return assignments
    text = workstreams_path.read_text()
    # Find the appendix table
    appendix = re.search(r"## Appendix.*?\n(.*)", text, re.DOTALL)
    if not appendix:
        return assignments
    table_text = appendix.group(1)
    for m in re.finditer(r"\|\s*`([^`]+)`\s*\|\s*(\w+)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|", table_text):
        slug = m.group(1)
        session = m.group(2).strip()
        track_str = m.group(3).strip()
        role = m.group(4).strip()
        if track_str == "—" or track_str == "-":
            assignments[slug] = {"track": None, "track_name": None, "role_in_track": role}
        else:
            track_num = None
            track_name = track_str
            num_match = re.match(r"(\d+)", track_str)
            if num_match:
                track_num = int(num_match.group(1))
            assignments[slug] = {"track": track_num, "track_name": track_str, "role_in_track": role}
    return assignments


def parse_tracks(workstreams_path: Path) -> list:
    """Parse track definitions from workstreams.md."""
    tracks = []
    if not workstreams_path.exists():
        return tracks
    text = workstreams_path.read_text()

    track_names = {
        0: "Shared Infrastructure",
        1: "GIAS Audit Planning Pipeline",
        2: "Evidence Collection & Extraction",
        3: "Compliance & Regulatory Assessment",
        4: "Reporting & Visualization",
        5: "AI Governance & Quality Assurance",
    }
    track_missions = {
        0: "Build the foundation that all other tracks depend on. First 2 hours: build. Rest of day: helpdesk.",
        1: "Run the full UC1-UC9 audit planning pipeline against synthetic data and produce a complete RCM + Work Program.",
        2: "Build and test evidence extraction pipelines for 4 different evidence types.",
        3: "Run framework-specific compliance assessments against synthetic data. Produce gap reports with regulatory citations.",
        4: "Convert raw findings from Tracks 1-3 into polished audit reports and visual dashboards.",
        5: "Be the second pair of eyes for every other track. Test agents for security, validate findings for accuracy.",
    }
    # Team compositions per table for 80 participants / 10 tables (~6-8 per table)
    # Track 1 and 3 each get 2 tables, so these are per-table targets
    track_teams = {
        0: {"engineers": 4, "analysts": 2},
        1: {"auditors": 3, "vaktechniek": 2, "analysts": 2, "engineers": 1},
        2: {"auditors": 2, "vaktechniek": 1, "analysts": 2, "engineers": 1},
        3: {"auditors": 2, "vaktechniek": 3, "analysts": 2, "engineers": 1},
        4: {"auditors": 2, "analysts": 2, "engineers": 2},
        5: {"auditors": 1, "vaktechniek": 2, "analysts": 1, "engineers": 2},
    }

    for i in range(6):
        tracks.append({
            "id": i,
            "name": f"Track {i}: {track_names[i]}",
            "short_name": track_names[i],
            "mission": track_missions[i],
            "team": track_teams[i],
        })
    return tracks


def parse_gaps(gap_path: Path) -> list:
    """Parse 53 audit domains with coverage status from gap-analysis.md."""
    gaps = []
    if not gap_path.exists():
        return gaps
    text = gap_path.read_text()
    current_category = ""
    for line in text.split("\n"):
        cat_match = re.match(r"## \d+\.\s+(.+)", line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue
        row_match = re.match(
            r"\|\s*([^|]+?)\s*\|\s*(✅[^|]*|⚠️[^|]*|❌[^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|",
            line,
        )
        if row_match and current_category:
            domain = row_match.group(1).strip()
            status_raw = row_match.group(2).strip()
            plans = row_match.group(3).strip()
            notes = row_match.group(4).strip()
            if domain in ("Domain", "---"):
                continue
            status = "not_covered"
            if "✅" in status_raw:
                status = "covered"
            elif "⚠️" in status_raw:
                status = "partial"
            # Extract plan slugs from backtick references
            plan_slugs = re.findall(r"`([^`]+\.md)`", plans)
            gaps.append({
                "category": current_category,
                "domain": domain,
                "status": status,
                "covering_plans": [s.replace(".md", "") for s in plan_slugs],
                "notes": notes,
            })
    return gaps


ORG = "SAAF-Project"
PHASES = ("plan", "do", "check", "act")
# What one PDCA phase counts for. A plan's progress is the average of its four phases (see plan_progress below), and a
# part's or the project's progress is the average of its plans. The weights are written into progress.json, and the portal
# shows them in "How this is calculated" (saaf-portal: src/components/temple/derive.ts holds the same numbers).
PHASE_WEIGHTS = {
    "complete": 1.0,  # the phase is done: counts in full
    "in_progress": 0.5,  # started but not finished: counts as half, so a plan does not look finished too early
    "not_started": 0.0,  # nothing yet: counts as zero
}

# The "temple" layout of the progress visual: shared infrastructure is the foundation,
# the four audit stages are pillars (left to right), AI governance is the roof, and
# plans that are not in any track wait in the quarry.
TEMPLE_PARTS = [
    {"id": "foundation", "kind": "foundation", "track": 0, "stage": None, "position": 0},
    {"id": "planning", "kind": "pillar", "track": 1, "stage": "Planning", "position": 1},
    {"id": "collection", "kind": "pillar", "track": 2, "stage": "Collection & Extraction", "position": 2},
    {"id": "reporting", "kind": "pillar", "track": 4, "stage": "Reporting & Visualisation", "position": 3},
    {"id": "monitoring", "kind": "pillar", "track": 3, "stage": "Monitoring (Compliance & Regulatory)", "position": 4},
    {"id": "governance", "kind": "roof", "track": 5, "stage": None, "position": 5},
    {"id": "quarry", "kind": "quarry", "track": None, "stage": None, "position": 6},
]

REPO_LINK_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def load_json_config(path: Path) -> dict:
    """Load a curated JSON input; a missing file means no curation."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def normalise_sectors(raw: str, vocabulary: List[str]) -> Optional[List[str]]:
    """Split a 'Sector' cell into vocabulary values; None if it is an unfilled template placeholder."""
    raw = raw.strip()
    if not raw or raw.startswith("_") or " / " in raw:
        return None
    lookup = {v.lower(): v for v in vocabulary}
    sectors: List[str] = []
    for item in re.split(r"[;,]", raw):
        item = item.strip().strip("_*").strip()
        if not item:
            continue
        value = lookup.get(item.lower(), "Other")
        if value not in sectors:
            sectors.append(value)
    return sectors or None


def resolve_sectors(slug: str, meta: dict, organisation: str, cfg: dict) -> dict:
    """Sector tags for a plan: own Sector row > slug mapping > organisation rule > default."""
    vocabulary = cfg.get("vocabulary", ["General"])
    own = normalise_sectors(meta.get("sector", ""), vocabulary)
    if own:
        return {"sectors": own, "sector_source": "plan"}
    mapped = cfg.get("assignments", {}).get(slug)
    if mapped:
        return {"sectors": mapped, "sector_source": "mapping"}
    for org_name, sectors in cfg.get("organisation_rules", {}).items():
        if org_name.lower() in organisation.lower():
            return {"sectors": sectors, "sector_source": "organisation"}
    return {"sectors": [cfg.get("default", "General")], "sector_source": "default"}


def repo_record(owner: str, name: str, source: str) -> dict:
    name = re.sub(r"\.git$", "", name).rstrip(".")
    return {"name": name, "url": f"https://github.com/{owner}/{name}", "source": source}


def mapped_repo(target: str) -> dict:
    """Repo record for a mapping value: 'Repo' (in the SAAF-Project org) or 'owner/Repo'."""
    owner, _, name = target.rpartition("/")
    return repo_record(owner or ORG, name, "mapping")


def resolve_repo(slug: str, meta: dict, text: str, cfg: dict) -> Optional[dict]:
    """Primary agent repo of a plan: mapping > Repository row > most-linked SAAF-Project repo in the text."""
    assignments = cfg.get("assignments", {})
    if slug in assignments:
        target = assignments[slug]
        if target is None:
            return None
        if isinstance(target, dict):
            target = target["primary"]
        return mapped_repo(target)

    linked = REPO_LINK_RE.search(meta.get("repository", ""))
    if linked:
        return repo_record(linked.group(1), linked.group(2), "plan-metadata")

    ignored = {r.lower() for r in cfg.get("ignore_repos", [])}
    counts: Dict[str, int] = {}
    for owner, name in REPO_LINK_RE.findall(text):
        clean = re.sub(r"\.git$", "", name).rstrip(".")
        if owner.lower() == ORG.lower() and clean.lower() not in ignored:
            counts[clean] = counts.get(clean, 0) + 1
    if counts:
        best = max(counts, key=lambda n: counts[n])  # first-seen wins ties
        return repo_record(ORG, best, "text-link")
    return None


def resolve_repo_alternatives(slug: str, cfg: dict) -> List[dict]:
    """Other repos that hold (parts of) the same agent: candidates to archive or merge."""
    target = cfg.get("assignments", {}).get(slug)
    if not isinstance(target, dict):
        return []
    return [mapped_repo(dup) for dup in target.get("duplicates", [])]


MAIN_REPO_URL = f"https://github.com/{ORG}/{ORG}/tree/main"
MAIN_REPO_PATH_RE = re.compile(r"tools/(?:scripts|strapi|apis|automation|integrations)/[\w./\-]*\w")


def resolve_main_repo_code(slug: str, text: str, cfg: dict) -> dict:
    """Code of a plan that lives inside this (main) repo: curated paths plus existing paths named in the plan.

    Plans also name paths they only *propose* to build, so every path must exist on disk.
    """
    entry = cfg.get("main_repo_code", {}).get(slug, {})
    ignored = tuple(cfg.get("main_repo_ignore_prefixes", []))
    items: List[dict] = []
    seen = set()

    def add(path: str, source: str) -> None:
        path = path.rstrip("/")
        if path in seen or any(path.startswith(p + "/") for p in seen) or not (ROOT / path).exists():
            return
        seen.add(path)
        items.append({"path": path, "url": f"{MAIN_REPO_URL}/{path}", "source": source})

    for path in entry.get("paths", []):
        add(path, "mapping")
    for path in MAIN_REPO_PATH_RE.findall(text):
        if not path.startswith(ignored):
            add(path, "plan-text")
    return {"code": items, "note": entry.get("note", "")}


def repo_status(repo: Optional[dict], alternatives: List[dict], code: List[dict], not_needed: bool) -> str:
    """dedicated | duplicate | main-repo | missing | not-needed (what a plan needs to do about its repo)."""
    if repo and (alternatives or code):
        return "duplicate"
    if repo:
        return "dedicated"
    if code:
        return "main-repo"
    return "not-needed" if not_needed else "missing"


def repo_note(slug: str, cfg: dict, main_code_note: str) -> str:
    """Curated explanation of a plan's repo situation (assignment note plus main-repo note)."""
    target = cfg.get("assignments", {}).get(slug)
    notes = [target.get("note", "") if isinstance(target, dict) else "", main_code_note]
    return " ".join(n for n in notes if n)


def repo_not_needed(plan_type: str, slug: str, cfg: dict) -> bool:
    """Reference/framework plans and curated strategy plans are not expected to have a repo."""
    t = plan_type.strip().lower()
    return t.startswith("reference") or t == "framework" or slug in cfg.get("no_repo_needed", {})


REPO_GUIDANCE = {
    "config": {
        "mapping_file": "plans/metadata/plan-repos.json",
        "plan_row": "the 'Repository' row in section 1 of the plan",
        "refresh": "The visual updates after the next dashboard run (GitHub Action on pushes to main that touch plans/).",
    },
    "duplicate": {
        "title": "Possible duplicate repositories",
        "steps": [
            "Confirm the canonical repo: the latest one that carries an AUDIT-CRITERIA.md (shown as primary).",
            "To change it, set 'primary' for the plan in plans/metadata/plan-repos.json (or the plan's 'Repository' row) and open a PR (fork, branch your-name/feature-description).",
            "Move any unique code or docs from the other repo into the canonical repo through a PR there, so history and credit are kept.",
            "Archive the other repo on GitHub (Settings, Archive) and add a README pointer to the canonical repo, instead of deleting it.",
            "Remove it from 'duplicates' in plans/metadata/plan-repos.json once archived.",
        ],
    },
    "main-repo": {
        "title": "Built inside the main repository",
        "steps": [
            "Create a dedicated repo for the agent in the SAAF-Project org (one repo per agent); see docs/getting-started.md#building-an-agent.",
            "Copy the code with its README and add an AUDIT-CRITERIA.md next to the README; the /harden-agent-repo skill walks you through it.",
            "Open a PR in SAAF-Project that removes the code from the main repo and links the new repo. You keep your contribution history and earn the Agent Builder bonus.",
            "Set the new repo as 'primary' in plans/metadata/plan-repos.json (or the plan's 'Repository' row) and remove the 'main_repo_code' entry.",
            "Shared tooling (for example the Strapi sandbox) may legitimately stay in tools/.",
        ],
    },
    "missing": {
        "title": "No repository linked",
        "steps": [
            "If the agent exists, set the plan's 'Repository' row or add an assignment in plans/metadata/plan-repos.json.",
            "If it was built inside the main repo, add a 'main_repo_code' entry with its path.",
            "If it is not built yet, create a dedicated repo when work starts and link it.",
            "Strategy or reference plans that are not expected to have a repo go under 'no_repo_needed'.",
        ],
    },
}


STAGES = [
    {"id": 0, "key": "draft-plan", "label": "Draft plan", "hint": "The plan is not complete yet, or it has no PDCA table"},
    {"id": 1, "key": "final-plan", "label": "Final plan", "hint": "The plan is complete; nothing is built yet"},
    {"id": 2, "key": "building", "label": "Building", "hint": "Work has started (PDCA: Do in progress)"},
    {"id": 3, "key": "ready", "label": "Ready", "hint": "Do is complete; not tested yet"},
    {"id": 4, "key": "tested", "label": "Tested", "hint": "Check has started or is done"},
    {"id": 5, "key": "improving", "label": "Improving", "hint": "Act has started or is done"},
]
KINDS = ["agent", "workflow", "skill", "document", "unspecified"]
STALE_DAYS = 90


def plan_kind(type_text: str) -> str:
    """Kind of a plan from the free text of its Type row ('Framework + Workflow' counts as a workflow)."""
    t = (type_text or "").strip().lower()
    if t.startswith("agent"):
        return "agent"
    if "workflow" in t:
        return "workflow"
    if "skill" in t:
        return "skill"
    if "reference" in t or "framework" in t:
        return "document"
    return "unspecified"


def has_build_evidence(status: str) -> bool:
    """A repo (own, or one of several) or code in the main repo: something that can be shown."""
    return status in ("dedicated", "duplicate", "main-repo")


def claimed_stage(pdca: dict, pdca_known: bool) -> int:
    """The stage the plan's own PDCA table claims (ignoring any evidence)."""
    if not pdca_known:
        return 0
    if pdca["act"] != "not_started":
        return 5
    if pdca["check"] != "not_started":
        return 4
    if pdca["do"] == "complete":
        return 3
    if pdca["do"] == "in_progress":
        return 2
    return 1 if pdca["plan"] == "complete" else 0


def stage_of(kind: str, pdca: dict, pdca_known: bool, status: str) -> int:
    """Stage of a plan: what its PDCA table claims, held back where it must be shown.

    - No PDCA table: Draft plan, until there is one.
    - An agent only leaves the plan stages when a repo (or code) can be shown; without one it stays in
      Draft plan / Final plan and an alert says what the plan claims.
    """
    claimed = claimed_stage(pdca, pdca_known)
    if claimed >= 2 and kind == "agent" and not has_build_evidence(status):
        return 1 if pdca["plan"] == "complete" else 0
    return claimed


ALERT_CATALOG = [
    {"id": "duplicate-repos", "severity": "error", "label": "Duplicate repos", "hint": "The same agent lives in more than one repo: pick the canonical one and archive the rest (see the Repo Annex)"},
    {"id": "claims-building-no-repo", "severity": "error", "label": "Building without a repo", "hint": "An agent whose PDCA says work has started, but no repo or code is linked: it stays in its plan stage"},
    {"id": "pdca-missing", "severity": "error", "label": "PDCA missing", "hint": "The plan has no PDCA table, so it stays in Draft plan until it has one"},
    {"id": "pdca-out-of-sync", "severity": "error", "label": "PDCA out of sync", "hint": "A later PDCA phase is further along than an earlier one"},
    {"id": "repo-not-started", "severity": "warning", "label": "Repo, but Do not started", "hint": "A repo is linked, but the PDCA table says Do has not started"},
    {"id": "repo-shared", "severity": "warning", "label": "Repo shared by plans", "hint": "Two or more plans point at the same repo: one repo per agent, so check which plan it really belongs to"},
    {"id": "status-draft", "severity": "info", "label": "Status still Draft", "hint": "The plan is complete (PDCA), but its Status row still says Draft. The template says: Finalised once your PR is merged"},
    {"id": "pdca-stale", "severity": "info", "label": "PDCA not updated for %d+ days" % STALE_DAYS, "hint": "Do is in progress, but the plan has not been touched for a long time: check the PDCA table"},
    {"id": "proposed-track", "severity": "info", "label": "Placement to confirm", "hint": "The plan is not in the Hackathon #3 workstreams list, so its place in the picture is a proposal. It says nothing about the plan's progress or quality"},
]


def plan_status_kind(status: str) -> str:
    s = (status or "").lower()
    for k in ("finalised", "presented", "draft"):
        if s.startswith(k):
            return k
    return "other"


def plan_alerts(rec: dict, today: Optional[datetime.date] = None, track_names: Optional[Dict[int, str]] = None) -> List[dict]:
    """Quality alerts of one plan record (as built in build_progress). Order follows ALERT_CATALOG."""
    out: List[dict] = []
    pdca, known, kind = rec["pdca"], rec["pdca_known"], rec["kind"]

    def add(alert_id: str, message: str) -> None:
        severity = next(a["severity"] for a in ALERT_CATALOG if a["id"] == alert_id)
        out.append({"id": alert_id, "severity": severity, "message": message})

    if rec["repo_status"] == "duplicate":
        homes = ([rec["repo"]["name"] + " (primary)"] if rec["repo"] else []) + [a["name"] for a in rec["repo_alternatives"]]
        if rec["main_repo_code"]:
            homes.append("a copy in the main repo")
        add("duplicate-repos", "Held in more than one place: " + ", ".join(homes) + ".")
    if kind == "agent" and claimed_stage(pdca, known) >= 2 and not has_build_evidence(rec["repo_status"]):
        add("claims-building-no-repo", "The PDCA table says work has started, but no repo or code is linked, so the plan stays in %s." % STAGES[rec["stage"]]["label"])
    if not known:
        add("pdca-missing", "The plan has no PDCA table, so it stays in Draft plan until it has one.")
    elif any(PHASE_WEIGHTS[pdca[b]] > PHASE_WEIGHTS[pdca[a]] for a, b in zip(PHASES, PHASES[1:])):
        add("pdca-out-of-sync", "A later PDCA phase is further along than an earlier one (Plan %s, Do %s, Check %s, Act %s)." % tuple(pdca[k].replace("_", " ") for k in PHASES))
    if rec["repo_status"] in ("dedicated", "duplicate") and known and pdca["do"] == "not_started" and pdca["check"] == "not_started" and pdca["act"] == "not_started":
        add("repo-not-started", "A repo is linked (%s), but the PDCA table says Do has not started." % rec["repo"]["name"])
    if known and pdca["plan"] == "complete" and plan_status_kind(rec["status"]) == "draft":
        add("status-draft", "The plan is complete, but its Status row still says Draft.")
    if known and pdca["do"] == "in_progress" and rec.get("updated") and today:
        days = (today - datetime.date.fromisoformat(rec["updated"])).days
        if days > STALE_DAYS:
            add("pdca-stale", "Do is in progress, but the plan was last updated on %s (%d days ago)." % (rec["updated"], days))
    if rec["track_source"] == "proposed":
        where = "Track %s" % rec["track"] + (" (%s)" % track_names[rec["track"]] if track_names and rec["track"] in track_names else "")
        add("proposed-track", "Not a problem with the plan: it is not in the Hackathon #3 workstreams list, so it was placed in %s as a proposal (%s). The owner can confirm or change this placement." % (where, rec["track_reason"] or "no reason given"))
    return out


def add_shared_repo_alerts(plan_records: List[dict]) -> None:
    """Alert on plans whose primary repo is also the primary repo of another plan. Needs all plans, so it runs after plan_alerts."""
    by_repo: Dict[str, List[dict]] = {}
    for rec in plan_records:
        if rec["repo"]:
            by_repo.setdefault(rec["repo"]["name"].lower(), []).append(rec)
    order = {a["id"]: i for i, a in enumerate(ALERT_CATALOG)}
    severity = next(a["severity"] for a in ALERT_CATALOG if a["id"] == "repo-shared")
    for sharers in by_repo.values():
        if len(sharers) < 2:
            continue
        for rec in sharers:
            others = ", ".join(sorted(o["slug"] for o in sharers if o is not rec))
            rec["alerts"].append({"id": "repo-shared", "severity": severity, "message": "Repo %s is also linked from: %s." % (rec["repo"]["name"], others)})
            rec["alerts"].sort(key=lambda a: order[a["id"]])


def is_shallow_clone() -> bool:
    """A shallow clone has no history, so every file looks 'just changed': file ages are then not used."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"], capture_output=True, text=True, timeout=20).stdout.strip()
        return out != "false"
    except Exception:
        return True


def git_last_commit_date(path: Path) -> Optional[str]:
    """Date (YYYY-MM-DD) of the last commit that touched a file, or None if unknown."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%cs", "--", str(path.relative_to(ROOT))], capture_output=True, text=True, timeout=20).stdout.strip()
        return out or None
    except Exception:
        return None


def plan_progress(pdca: dict) -> float:
    """Mean phase weight over Plan/Do/Check/Act (complete 1, in progress 0.5, not started 0)."""
    return round(sum(PHASE_WEIGHTS[pdca[ph]] for ph in PHASES) / len(PHASES), 3)


def rollup(plan_records: List[dict]) -> dict:
    """Aggregate progress over plans; plans without a PDCA table are counted but not averaged."""
    known = [p for p in plan_records if p["pdca_known"]]
    phases = {"complete": 0, "in_progress": 0, "not_started": 0}
    phase_sum = {ph: 0.0 for ph in PHASES}
    for p in known:
        for ph in PHASES:
            phases[p["pdca"][ph]] += 1
            phase_sum[ph] += PHASE_WEIGHTS[p["pdca"][ph]]
    n = len(known)
    statuses: Dict[str, int] = {}
    for p in plan_records:
        statuses[p["repo_status"]] = statuses.get(p["repo_status"], 0) + 1
    return {
        "plan_count": len(plan_records),
        "plans_unknown": len(plan_records) - n,
        "progress": round(sum(p["progress"] for p in known) / n, 3) if n else None,
        "phase_progress": {ph: (round(phase_sum[ph] / n, 3) if n else None) for ph in PHASES},
        "phases": phases,
        "repo_count": sum(1 for p in plan_records if p["repo"]),
        "repo_status": statuses,
    }


def build_progress(plans: List[dict], extras: Dict[str, dict], tracks: List[dict], sector_cfg: dict,
                   track_cfg: Optional[dict] = None, today: Optional[datetime.date] = None) -> dict:
    """Build the project -> part -> plan -> phase hierarchy used by the progress visual.

    Plans without a workstream track use the proposed track from plans/metadata/track-proposals.json
    (marked track_source "proposed"); plans with neither stay in the quarry.
    """
    proposals = (track_cfg or {}).get("proposals", {})
    track_by_id = {t["id"]: t for t in tracks}
    part_by_track = {p["track"]: p["id"] for p in TEMPLE_PARTS if p["track"] is not None}

    plan_records = []
    for p in plans:
        ex = extras[p["slug"]]
        proposal = proposals.get(p["slug"])
        if p["track"] is not None:
            track, track_source, track_reason = p["track"], "workstreams", ""
        elif proposal:
            track, track_source, track_reason = proposal["track"], "proposed", proposal.get("reason", "")
        else:
            track, track_source, track_reason = None, "none", ""
        plan_records.append({
            "slug": p["slug"],
            "title": p["title"],
            "session": p["session"],
            "part": part_by_track.get(track, "quarry"),
            "track": track,
            "track_source": track_source,
            "track_reason": track_reason,
            "type": p["type"],
            "status": p["status"],
            "pdca": p["pdca"],
            "pdca_known": ex["pdca_known"],
            "progress": plan_progress(p["pdca"]),
            "quality_score": p["quality_score"],
            "organisation": p["organisation"],
            "submitter": p["submitter"],
            "claimed_by": p["claimed_by"],
            "sectors": ex["sectors"],
            "sector_source": ex["sector_source"],
            "repo": ex["repo"],
            "repo_alternatives": ex["repo_alternatives"],
            "main_repo_code": ex["main_repo_code"],
            "repo_note": ex["repo_note"],
            "repo_status": ex["repo_status"],
            "github_url": p["github_url"],
            "problem_summary": p["problem_summary"],
            "updated": ex.get("updated"),
        })
        rec = plan_records[-1]
        rec["kind"] = plan_kind(p["type"])
        rec["stage"] = stage_of(rec["kind"], rec["pdca"], rec["pdca_known"], rec["repo_status"])
        rec["stage_key"] = STAGES[rec["stage"]]["key"]
        rec["alerts"] = plan_alerts(rec, today, {t: v["short_name"] for t, v in track_by_id.items()})
    add_shared_repo_alerts(plan_records)

    parts = []
    for part in TEMPLE_PARTS:
        members = [p for p in plan_records if p["part"] == part["id"]]
        track = track_by_id.get(part["track"]) if part["track"] is not None else None
        parts.append({
            **part,
            "name": track["short_name"] if track else "Not yet assigned to a track",
            "mission": track["mission"] if track else "Plans submitted outside the Hackathon #3 track structure.",
            "team": track["team"] if track else {},
            "plans": [p["slug"] for p in members],
            **rollup(members),
        })

    # The annex (side building) collects plans whose repo situation needs consolidation:
    # duplicate repos, and agents built inside this main repo that should move out.
    annex_items = [
        {
            "plan": p["slug"],
            "title": p["title"],
            "part": p["part"],
            "status": p["repo_status"],
            "primary": p["repo"],
            "duplicates": p["repo_alternatives"],
            "main_repo_code": p["main_repo_code"],
            "note": p["repo_note"],
        }
        for p in plan_records
        if p["repo_status"] in ("duplicate", "main-repo")
    ]

    sectors = sector_cfg.get("vocabulary", [])
    return {
        "schema_version": 2,
        "generated": today.isoformat() if today else None,  # a date, not a time: regenerating on the same day changes nothing
        "weights": PHASE_WEIGHTS,
        "stages": STAGES,
        "kinds": KINDS,
        "alert_catalog": ALERT_CATALOG,
        "sector_vocabulary": sectors,
        "project": {"name": "SAAF", **rollup(plan_records)},
        "parts": parts,
        "annex": {"name": "Repo Annex", "items": annex_items, "guidance": REPO_GUIDANCE},
        "plans": plan_records,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sector_cfg = load_json_config(META_DIR / "sectors.json")
    repo_cfg = load_json_config(META_DIR / "plan-repos.json")
    track_cfg = load_json_config(META_DIR / "track-proposals.json")
    extras: Dict[str, dict] = {}
    shallow = is_shallow_clone()
    if shallow:
        log.warning("Shallow git clone: plan file ages are unknown, so the 'PDCA not updated' alert is skipped "
                    "(check out with fetch-depth: 0).")

    quality_scores = parse_quality_scores(PLANS_DIR / "overview.md")
    overview_domains = parse_overview_domains(PLANS_DIR / "overview.md")
    track_assignments = parse_track_assignments(PLANS_DIR / "hackathon-3-workstreams.md")
    tracks = parse_tracks(PLANS_DIR / "hackathon-3-workstreams.md")
    gaps = parse_gaps(PLANS_DIR / "gap-analysis.md")

    plans = []
    for session, plan_dir in PLAN_DIRS:
        if not plan_dir.exists():
            continue
        for md_file in sorted(plan_dir.glob("*.md")):
            if md_file.name.lower() == "readme.md":
                continue
            slug = md_file.stem
            text = md_file.read_text()

            meta = parse_metadata_table(text)
            pdca = parse_pdca(text)
            title = parse_title(text)
            # Prefer curated domain description from overview.md over raw H1
            if slug in overview_domains:
                title = overview_domains[slug]
            elif title == TEMPLATE_TITLE:
                title = slug

            # Normalize submitter
            submitter = meta.get("submitter", "")
            if "on behalf of" in submitter.lower():
                submitter = re.sub(
                    r"Mathijs Schouten \(on behalf of (.+?)\)",
                    r"\1",
                    submitter,
                )

            # Track assignment
            ta = track_assignments.get(slug, {})

            plan = {
                "slug": slug,
                "title": title,
                "session": session,
                "submitter": submitter,
                "organisation": meta.get("organisation", meta.get("organization", "")),
                "type": meta.get("type", ""),
                "domain": meta.get("primary_domain", meta.get("domain", "")),
                "status": meta.get("status", "Draft"),
                "claimed_by": meta.get("claimed_by", ""),
                "pdca": pdca,
                "quality_score": quality_scores.get(slug, 0),
                "track": ta.get("track"),
                "track_name": ta.get("track_name"),
                "role_in_track": ta.get("role_in_track", ""),
                "problem_summary": parse_problem_summary(text),
                "github_url": meta.get("repository") or f"{GITHUB_BASE}/{session}/{md_file.name}",
            }
            plans.append(plan)
            repo = resolve_repo(slug, meta, text, repo_cfg)
            alternatives = resolve_repo_alternatives(slug, repo_cfg)
            main_code = resolve_main_repo_code(slug, text, repo_cfg)
            extras[slug] = {
                "updated": None if shallow else git_last_commit_date(md_file),
                "pdca_known": has_pdca(text),
                **resolve_sectors(slug, meta, plan["organisation"], sector_cfg),
                "repo": repo,
                "repo_alternatives": alternatives,
                "main_repo_code": main_code["code"],
                "repo_note": repo_note(slug, repo_cfg, main_code["note"]),
                "repo_status": repo_status(
                    repo, alternatives, main_code["code"],
                    repo_not_needed(plan["type"], slug, repo_cfg),
                ),
            }

    # Build submitters list (unique names → their plan slugs)
    submitter_map: dict = {}
    for p in plans:
        name = p["submitter"]
        if not name or name.lower() in ("unknown", "example participant (synthetic — for illustration only)"):
            continue
        # Split multi-person submitters (skip split for group names with parentheses)
        persons = [name] if "(" in name else re.split(r",\s*", name)
        for person in persons:
            person = person.strip()
            if not person:
                continue
            submitter_map.setdefault(person, []).append(p["slug"])
    submitters = [{"name": k, "plans": v} for k, v in sorted(submitter_map.items())]

    # Write outputs
    (OUT_DIR / "plans.json").write_text(json.dumps(plans, indent=2, ensure_ascii=False))
    (OUT_DIR / "tracks.json").write_text(json.dumps(tracks, indent=2, ensure_ascii=False))
    (OUT_DIR / "gaps.json").write_text(json.dumps(gaps, indent=2, ensure_ascii=False))
    (OUT_DIR / "submitters.json").write_text(json.dumps(submitters, indent=2, ensure_ascii=False))
    progress = build_progress(plans, extras, tracks, sector_cfg, track_cfg, datetime.date.today())
    (OUT_DIR / "progress.json").write_text(json.dumps(progress, indent=2, ensure_ascii=False))

    # Stats
    tracked = sum(1 for p in plans if p["track"] is not None)
    log.info("Generated dashboard data: %d plans (%d in tracks), %d tracks, %d domains, %d submitters",
             len(plans), tracked, len(tracks), len(gaps), len(submitters))
    log.info("Output: %s/", OUT_DIR)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
