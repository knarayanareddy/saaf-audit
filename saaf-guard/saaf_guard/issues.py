"""Bevindingen automatisch melden in de online repos (GitHub), veilig en zonder dubbelingen.

- Eén issue per repo met een afvinklijst (minder notificaties dan één issue per bevinding).
- Herkenbaar aan een onzichtbare marker; een volgende run WERKT HET BESTAANDE ISSUE BIJ i.p.v. een nieuw te maken.
- Privé repos: gewoon issue.
- Publieke repos: nooit een publiek issue (dat zou een open lek openbaar maken). Staat GitHub Private
  Vulnerability Reporting aan, dan een privé melding aan de beheerders; anders overslaan met advies.
- Standaard een PROEFRUN: schrijft de issue-teksten naar --preview en toont het plan. Pas met --apply wordt er iets aangemaakt.
- Alleen review-bevindingen (niet-geverifieerde zijn als zodanig gemarkeerd), tenzij --include-auto (heuristiek).

Gebruik:
  python -m saaf_guard.issues --findings scan-out/findings.json --org SAAF-Project [--apply] [--repos a,b] [--include-auto]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict

from .report import CAUSES, RATINGS, SECRET, infer_cause

MARKER = "<!-- saaf-guard-report:v1 -->"
GH = shutil.which("gh") or "gh"


def gh(*args, input_text: str | None = None, check: bool = True) -> str:
    r = subprocess.run([GH, *args], input=input_text, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}…: {r.stderr.strip()[:300]}")
    return r.stdout


def repo_info(org: str, repo: str) -> dict:
    info = json.loads(gh("repo", "view", f"{org}/{repo}", "--json", "visibility,hasIssuesEnabled"))
    pvr = False
    if info.get("visibility") == "PUBLIC":
        try:
            pvr = bool(json.loads(gh("api", f"repos/{org}/{repo}/private-vulnerability-reporting")).get("enabled"))
        except (RuntimeError, ValueError):
            pvr = False
    return {"visibility": info.get("visibility"), "issues": info.get("hasIssuesEnabled"), "pvr": pvr}


def existing_issue(org: str, repo: str) -> int | None:
    out = gh("issue", "list", "-R", f"{org}/{repo}", "--state", "open", "--search", "saaf-guard-report in:body",
             "--json", "number,body", "--limit", "20")
    for it in json.loads(out or "[]"):
        if MARKER in (it.get("body") or ""):
            return it["number"]
    return None


def build_body(repo: str, items: list[dict], date: str) -> tuple[str, str]:
    cnt = {k: sum(f["risk_rating"] == k for f in items) for k in RATINGS}
    sev = ", ".join(f"{cnt[k]} {k}" for k in RATINGS if cnt[k])
    title = f"Security review: {len(items)} finding(s) ({sev}) — SAAF Guard"
    lines = [
        MARKER,
        f"## Security review — {repo}",
        "",
        f"During the authorised **SAAF Security Challenge** ({date}) this repository was reviewed statically on a local copy "
        "(no live systems tested). This issue lists what was found, so it can be fixed. "
        "**Please do not paste secret values or personal data in comments.**",
        "",
        f"**Summary:** {sev}. Tick an item when it is fixed or explain why it does not apply.",
        "",
    ]
    for f in sorted(items, key=lambda x: (RATINGS.index(x["risk_rating"]), x["title"].lower())):
        cause = infer_cause(f)
        rules = ", ".join(str(r) for r in CAUSES[cause][0])
        verified = "verified" if str(f.get("verified")).lower() == "yes" else "not verified"
        loc = f" — `{f['location']}`" if f.get("location") else ""
        lines += [
            f"- [ ] **{f['risk_rating']}** · {f['title']}{loc}",
            "  <details><summary>Details</summary>",
            "",
            f"  **Observation.** {f['observation']}",
            "",
            f"  **Recommendation.** {f['recommendation']}",
            "",
            f"  _{verified} · root cause: {CAUSES[cause][2]} · SAAF Guard build rule {rules}_",
            "  </details>",
        ]
    lines += [
        "",
        "---",
        "Prevent recurrence: the `saaf-guard` skill (nine build rules), safe building blocks and CI check in "
        "`SAAF-Project/saaf-guard` (`python -m saaf_guard.check . --history`). "
        "This issue is maintained automatically; a new scan updates it instead of opening a new one.",
    ]
    body = "\n".join(lines)
    if SECRET.search(body):
        raise ValueError(f"Sleutelachtige waarde in issue-tekst voor {repo} — afgebroken")
    if len(body) > 60_000:
        raise ValueError(f"Issue-tekst voor {repo} te lang ({len(body)} tekens)")
    return title, body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bevindingen melden als GitHub-issues (proefrun tenzij --apply)")
    ap.add_argument("--findings", required=True, help="findings.json van saaf_guard.scan")
    ap.add_argument("--org", required=True)
    ap.add_argument("--repos", help="kommagescheiden subset")
    ap.add_argument("--include-auto", action="store_true", help="ook automatische (onbevestigde) meldingen")
    ap.add_argument("--preview", default="issues-preview", help="map voor de issue-teksten (proefrun)")
    ap.add_argument("--apply", action="store_true", help="echt aanmaken/bijwerken op GitHub")
    a = ap.parse_args(argv)

    findings = json.load(open(a.findings, encoding="utf-8"))
    if not a.include_auto:
        findings = [f for f in findings if f.get("source") != "guard"]
    only = set(a.repos.split(",")) if a.repos else None
    per = defaultdict(list)
    for f in findings:
        if not only or f["repo"] in only:
            per[f["repo"]].append(f)

    os.makedirs(a.preview, exist_ok=True)
    date = dt.date.today().isoformat()
    plan = []
    for repo in sorted(per, key=str.lower):
        title, body = build_body(repo, per[repo], date)
        with open(os.path.join(a.preview, f"{repo}.md"), "w", encoding="utf-8") as fh:
            fh.write(f"# {title}\n\n{body}\n")
        try:
            info = repo_info(a.org, repo)
        except RuntimeError as e:
            plan.append(dict(repo=repo, action="fout", detail=str(e)[:120], n=len(per[repo])))
            continue
        if info["visibility"] == "PUBLIC":
            action = "privé-melding (PVR)" if info["pvr"] else "OVERGESLAGEN: publiek, PVR uit"
            num = None
        elif not info["issues"]:
            action, num = "OVERGESLAGEN: issues uit", None
        else:
            num = existing_issue(a.org, repo)
            action = f"bijwerken #{num}" if num else "nieuw issue"
        plan.append(dict(repo=repo, action=action, n=len(per[repo]), title=title, number=num,
                         visibility=info["visibility"]))

        if not a.apply or action.startswith(("OVERGESLAGEN", "fout")):
            continue
        try:
            if action == "nieuw issue":
                url = gh("issue", "create", "-R", f"{a.org}/{repo}", "--title", title, "--body-file", "-", input_text=body).strip()
                plan[-1]["result"] = url
            elif action.startswith("bijwerken"):
                gh("issue", "edit", str(num), "-R", f"{a.org}/{repo}", "--title", title, "--body-file", "-", input_text=body)
                plan[-1]["result"] = f"bijgewerkt #{num}"
            else:  # privé kwetsbaarheidsmelding bij publieke repo
                top = max((f["risk_rating"] for f in per[repo]), key=lambda r: -RATINGS.index(r))
                sev = {"Critical": "critical", "High": "high", "Medium": "medium"}.get(top, "low")
                payload = json.dumps({"summary": title[:1000], "description": body, "severity": sev})
                out = gh("api", "-X", "POST", f"repos/{a.org}/{repo}/security-advisories/reports", "--input", "-",
                         input_text=payload)
                plan[-1]["result"] = json.loads(out).get("html_url", "gemeld")
        except RuntimeError as e:
            plan[-1]["result"] = f"FOUT: {str(e)[:150]}"

    for p in plan:  # issue-URL ook bij proefrun/bijwerken, voor het rapport
        if p.get("number") and not str(p.get("result", "")).startswith("http"):
            p["url"] = f"https://github.com/{a.org}/{p['repo']}/issues/{p['number']}"
        elif str(p.get("result", "")).startswith("http"):
            p["url"] = p["result"]
    plan_name = "plan.json" if not only else "plan-subset.json"  # deelrun overschrijft het volledige plan niet
    with open(os.path.join(a.preview, plan_name), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=1)
    mode = "UITGEVOERD" if a.apply else "PROEFRUN (niets aangemaakt; gebruik --apply)"
    print(f"{mode}: {len(plan)} repos, {sum(p['n'] for p in plan)} bevindingen")
    for p in plan:
        print(f"  {p['repo'][:42]:42} {p['n']:3}  {p['action']:32} {p.get('result', '')}")
    print(f"Issue-teksten: {os.path.abspath(a.preview)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
