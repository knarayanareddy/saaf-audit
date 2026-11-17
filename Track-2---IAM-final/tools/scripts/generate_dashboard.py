#!/usr/bin/env python3
"""Generate dashboard JSON data from SAAF plan Markdown files.

Reads all plan .md files, overview.md (quality scores), workstreams.md
(track assignments), and gap-analysis.md (domain coverage) and writes:
  - website/data/plans.json
  - website/data/tracks.json
  - website/data/gaps.json
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
PLANS_DIR = ROOT / "plans"
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


def parse_pdca(text: str) -> dict:
    """Extract PDCA status from Section 11."""
    pdca = {"plan": "not_started", "do": "not_started", "check": "not_started", "act": "not_started"}
    section_match = re.search(r"## 11\.\s*PDCA.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not section_match:
        return pdca
    section = section_match.group(1)
    for phase in ["plan", "do", "check", "act"]:
        pattern = rf"\*\*{phase.capitalize()}\*\*\s*\|\s*(.+?)\s*\|"
        m = re.search(pattern, section, re.IGNORECASE)
        if m:
            status_text = m.group(1).lower()
            if "complete" in status_text:
                pdca[phase] = "complete"
            elif "in progress" in status_text:
                pdca[phase] = "in_progress"
    return pdca


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


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

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
                "github_url": f"{GITHUB_BASE}/{session}/{md_file.name}",
            }
            plans.append(plan)

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

    # Stats
    tracked = sum(1 for p in plans if p["track"] is not None)
    print(f"Generated dashboard data: {len(plans)} plans ({tracked} in tracks), "
          f"{len(tracks)} tracks, {len(gaps)} domains, {len(submitters)} submitters")
    print(f"Output: {OUT_DIR}/")


if __name__ == "__main__":
    main()
