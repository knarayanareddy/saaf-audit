"""SAAF repo-scan agent: scan -> samenvoegen -> rapporteren (NL/EN).

Stappen
  1. repos vinden in een werkmap (submappen met .git), of --repos a,b,c
  2. SAAF Guard-check per repo (statisch, lokaal; optioneel --history voor sleutels in git)
  3. review-bevindingen inlezen (JSON van de saaf-security-reviewer agent), optioneel
  4. samenvoegen en ontdubbelen (zelfde oorzaak in hetzelfde bestand = één bevinding; review wint)
  5. uitvoer: findings.json, findings.csv (challenge-formaat), report.html (tweetalig)

Gebruik
  python -m saaf_guard.scan <werkmap> --out scan-out [--history] [--reviews map] [--team naam] [--lang nl|en]

Geen netwerk, geen LLM-aanroepen: dit is de deterministische kern. De inhoudelijke review gebeurt
door de saaf-security-reviewer agent (Claude Code), die JSON schrijft naar --reviews.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

from . import check
from .report import RULE_CAUSE, infer_cause, write_csv, write_html

SEVMAP = {"high": "High", "medium": "Medium", "low": "Low"}
SKIP = {"node_modules", ".venv", "venv", "__pycache__"}


def discover(workspace: str, only: list[str] | None = None) -> list[str]:
    if only:
        return [os.path.join(workspace, r) for r in only if os.path.isdir(os.path.join(workspace, r))]
    out = []
    for d in sorted(os.listdir(workspace)):
        p = os.path.join(workspace, d)
        if d.startswith((".", "_")) or d in SKIP or not os.path.isdir(p):
            continue
        if os.path.isdir(os.path.join(p, ".git")):
            out.append(p)
    return out


def guard_findings(repo_path: str, history: bool) -> list[dict]:
    """SAAF Guard-meldingen -> één bevinding per (repo, regel)."""
    repo = os.path.basename(os.path.normpath(repo_path))
    per_rule = defaultdict(list)
    for h in check.scan(repo_path, history=history):
        per_rule[h.rule].append(h)
    out = []
    for rule, hits in sorted(per_rule.items()):
        sev, title, fix = check.rule_text(rule)
        locs = [f"{h.path}:{h.line}" if h.line else h.path for h in hits]
        details = "; ".join(f"{l} ({h.detail})" for l, h in zip(locs[:8], hits[:8]))
        more = check.T(f" … en {len(hits) - 8} meer", f" … and {len(hits) - 8} more") if len(hits) > 8 else ""
        note = check.T("Automatisch gevonden door SAAF Guard (statische heuristiek); handmatig bevestigen.",
                       "Found automatically by SAAF Guard (static heuristic); confirm manually.")
        out.append({
            "title": f"{rule}: {title}",
            "repo": repo,
            "risk_rating": "Critical" if rule == "SG01" else SEVMAP[sev],
            "observation": f"{check.T(f'{len(hits)} plaats(en)', f'{len(hits)} location(s)')}: {details}{more}. {note}",
            "recommendation": fix,
            "verified": "no",
            "location": locs[0],
            "rule": rule,
            "cause": RULE_CAUSE[rule],
            "source": "guard",
        })
    return out


def load_dismissed(path: str | None) -> list[dict]:
    """Afgewezen automatische meldingen (na review): bestand of map met JSON-lijsten van {repo, rule, location?, reason}."""
    if not path:
        return []
    files = sorted(glob.glob(os.path.join(path, "*.json"))) if os.path.isdir(path) else [path]
    out = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            out += json.load(fh)
    return out


def apply_dismissed(guard: list[dict], dismissed: list[dict]) -> tuple[list[dict], int]:
    keys = {(d["repo"].lower(), d["rule"]) for d in dismissed if d.get("repo") and d.get("rule")}
    kept = [g for g in guard if (g["repo"].lower(), g.get("rule")) not in keys]
    return kept, len(guard) - len(kept)


def load_reviews(folder: str | None) -> list[dict]:
    if not folder:
        return []
    out = []
    for f in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        for x in data:
            x.setdefault("source", "review")
            out.append(x)
    return out


def _file(loc: str) -> str:
    return (loc or "").split(" @")[0].split(":")[0].replace("\\", "/").split("/")[-1].lower()


def merge(review: list[dict], guard: list[dict]) -> list[dict]:
    """Review-bevindingen gaan voor; een guard-melding vervalt als de review dezelfde oorzaak
    in hetzelfde bestand van dezelfde repo al beschrijft. Exacte dubbelen (repo+titel) vervallen."""
    seen, out = set(), []
    covered = {(r["repo"].lower(), infer_cause(r), _file(r.get("location", ""))) for r in review}
    for f in review + guard:
        key = (f["repo"].lower(), f["title"].strip().lower())
        if key in seen:
            continue
        if f.get("source") == "guard" and (f["repo"].lower(), f["cause"], _file(f.get("location", ""))) in covered:
            continue
        seen.add(key)
        out.append(f)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SAAF repo-scan agent (NL/EN)")
    ap.add_argument("workspace", help="map met repo-clones (submappen met .git)")
    ap.add_argument("--repos", help="kommagescheiden subset van repo-mappen")
    ap.add_argument("--reviews", help="map met review-JSON van de saaf-security-reviewer agent")
    ap.add_argument("--dismissed", help="bestand/map met afgewezen automatische meldingen (repo+rule) die niet meer gemeld worden")
    ap.add_argument("--out", default="scan-out")
    ap.add_argument("--history", action="store_true", help="ook git-geschiedenis op sleutels scannen (trager)")
    ap.add_argument("--team", default="", help="teamnaam voor de CSV-kolom 'team'")
    ap.add_argument("--lang", default=os.environ.get("SAAF_GUARD_LANG", "nl"), choices=["nl", "en"])
    ap.add_argument("--title", default="")
    ap.add_argument("--exclude", default="", help="kommagescheiden repo-mappen om over te slaan")
    ap.add_argument("--html", help="pad voor het HTML-rapport (standaard <out>/report.html)")
    ap.add_argument("--issues-plan", help="plan.json van saaf_guard.issues: toont het hoofdstuk 'Gemeld in de online repos'")
    ap.add_argument("--related", action="append", default=[],
                    help="verwijzing naar ander rapport: 'href|label_nl|label_en|uitleg_nl|uitleg_en' (herhaalbaar)")
    a = ap.parse_args(argv)
    check.set_lang(a.lang)

    repos = discover(a.workspace, a.repos.split(",") if a.repos else None)
    skip = {x.strip().lower() for x in a.exclude.split(",") if x.strip()}
    repos = [r for r in repos if os.path.basename(os.path.normpath(r)).lower() not in skip]
    if not repos:
        print(check.T("Geen repos gevonden.", "No repositories found."), file=sys.stderr)
        return 2
    guard = []
    for i, r in enumerate(repos, 1):
        print(f"[{i}/{len(repos)}] {os.path.basename(r)}", file=sys.stderr)
        guard += guard_findings(r, a.history)
    review = load_reviews(a.reviews)
    guard, n_dis = apply_dismissed(guard, load_dismissed(a.dismissed))
    findings = merge(review, guard)

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "findings.json"), "w", encoding="utf-8") as fh:
        json.dump([{k: v for k, v in f.items() if not k.startswith("_")} for f in findings], fh, ensure_ascii=False, indent=1)
    n = write_csv(findings, os.path.join(a.out, "findings.csv"), team=a.team)
    title = a.title or check.T("SAAF security scan — bevindingen", "SAAF security scan — findings")
    related = [tuple((r.split("|") + ["", "", "", ""])[:5]) for r in a.related]
    write_html(findings, a.html or os.path.join(a.out, "report.html"), lang=a.lang, title=title,
               repos=[os.path.basename(os.path.normpath(r)) for r in repos], related=related,
               issues_plan=json.load(open(a.issues_plan, encoding="utf-8")) if a.issues_plan else None)

    by = defaultdict(int)
    for f in findings:
        by[f["risk_rating"]] += 1
    print(check.T(f"\n{len(repos)} repos gescand: {n} bevindingen ({len(review)} uit review, {len(guard)} automatisch voor ontdubbelen, {n_dis} eerder afgewezen)",
                  f"\n{len(repos)} repos scanned: {n} findings ({len(review)} from review, {len(guard)} automatic before de-duplication, {n_dis} previously dismissed)"))
    print("  " + ", ".join(f"{k}: {by[k]}" for k in ("Critical", "High", "Medium", "Low") if by[k]))
    print(check.T(f"Uitvoer: {os.path.abspath(a.out)}", f"Output: {os.path.abspath(a.out)}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
