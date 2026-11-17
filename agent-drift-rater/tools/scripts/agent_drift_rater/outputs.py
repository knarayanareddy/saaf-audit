"""Produce committed artefacts from unit ratings: findings JSON, a scorecard, an HTML
dashboard, and per-unit advice. All text is templated; evidence is cited as path#line, never
as code. A leak check (``check_no_verbatim``) guards every committed string against the
fetched source before publication.
"""

import html
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from . import config
from .scoring import DIMENSION_NAMES, DRIVERS, CONTROLS, UnitRating, RedFlag

logger = logging.getLogger(__name__)

_RATING_CLASS = {"High": "r-high", "Medium": "r-med", "Low": "r-low", "Informational": "r-info"}

RED_FLAG_LABELS = {
    "RF1": "It can edit itself", "RF2": "A target in its context", "RF3": "Rules only in the prompt",
    "RF4": "Escalations falling", "RF5": "Softening language", "RF6": "No replayable log",
}

# Finding templates keyed by trigger. (title, control_objective, recommendation)
TEMPLATES = {
    "RF1": ("Agent can modify its own instructions or memory",
            "Drift Watch RF1; OWASP LLM04; EU AI Act Art. 15(4)",
            "Route instruction/memory changes through reviewed version control; forbid runtime "
            "self-edits of the prompt, rules, or tool list."),
    "RF2": ("Performance target in the agent's context",
            "Drift Watch RF2; EU AI Act Art. 9",
            "Remove self-performance scores/KPIs from the model's context, or isolate them from "
            "rule-bound decisions."),
    "RF3": ("Hard rule enforced only in the prompt",
            "Drift Watch RF3; OWASP LLM07; EU AI Act Art. 15",
            "Enforce each mandate hard rule in code before the action, with a test proving the "
            "guard blocks regardless of model output."),
    "RF6": ("No replayable decision log",
            "Drift Watch RF6; OWASP LLM02 (log hygiene); EU AI Act Art. 12",
            "Log per decision: input reference, instruction/prompt version, model id, tool calls "
            "and outcome (see audit_planning_orchestrator/run_logger.py)."),
    "D5": ("Capability beyond the documented mandate",
           "Drift Watch RF1/permission creep; OWASP LLM06; SAAF guardrails",
           "Apply least privilege: constrain tools to the mandate, use an allowlist, and remove "
           "shell/eval on model output."),
    "D4": ("Untrusted input reaches an action-capable path",
           "OWASP LLM01; EU AI Act Art. 15(5)",
           "Delimit untrusted content and treat it as data; gate privileged actions behind a code "
           "check, not the prompt."),
    "RF5": ("Softening language in agent-written notes",
            "Drift Watch RF5; EU AI Act Art. 12",
            "Review agent-written notes/memory before they re-enter the prompt; diff against the "
            "approved baseline."),
    "MANDATE": ("Mandate undocumented or thin",
                "Drift Watch (no approved mandate); EU AI Act Art. 11",
                "Document the agent's approved mandate (purpose, hard rules, approval points) so "
                "drift can be detected."),
    "INJ": ("Injection-like directive found in repository text",
            "OWASP LLM01 (prompt injection)",
            "Review the flagged text; ensure repository documents cannot steer the agent, and that "
            "the agent treats such content as data, not instructions."),
}

ADVICE_HOWTO = {
    "RF3": "Add a guard module (pattern: audit_planning_orchestrator/schemas.py) plus a pytest that "
           "feeds adversarial model output and asserts the action is blocked.",
    "RF6": "Adopt a run log with model id and a prompt hash per decision "
           "(audit_planning_orchestrator/run_logger.py).",
    "D5": "Introduce a tool/command allowlist (see regulatory/guardrails/allowed-commands.md).",
    "D4": "Wrap external content in delimiters and instruct the model to treat it as data.",
    "RF1": "Move memory/lesson writes behind PR review; never let the agent rewrite its own prompt.",
    "RF2": "Keep performance metrics out of the decision prompt.",
    "RF5": "Version agent-written notes and diff them against the approved baseline.",
}

EVIDENCE_REQUESTS = [
    "C1 — a test showing a hard-rule guard blocks a violating action regardless of the prompt",
    "C2 — the approved instruction baseline and how each version is diffed against it",
    "C3 — who performs independent drift review, the threshold, and how alerts are closed",
    "C4 — the rollback/quarantine procedure and evidence it has been exercised",
    "C5 — a decision log entry showing input, instruction+model version, tool calls and outcome",
]


def build_findings(rating: UnitRating, repo: str, web_url, prompt_only_rule_refs: List[str],
                   injection_refs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    raised = {f.rf: f for f in rating.red_flags if f.status == "raised"}

    def mk(key: str, risk: str, observation: str, refs: List[str]) -> Dict[str, Any]:
        title, objective, recommendation = TEMPLATES[key]
        return {
            "title": title[:100], "risk_rating": risk, "control_objective": objective,
            "observation": observation, "recommendation": recommendation,
            "ai_assisted": True, "status": "Open",
            "owner": f"Repository maintainers ({repo})",
            "evidence_references": [f"unit:{rating.unit_id}"] + refs,
        }

    for rf in ("RF1", "RF2", "RF3", "RF5", "RF6"):
        if rf in raised:
            risk = "High" if rating.residual in ("High", "Medium") and rf in ("RF1", "RF3") else "Medium"
            refs = raised[rf].evidence or (prompt_only_rule_refs if rf == "RF3" else [])
            findings.append(mk(rf, risk, raised[rf].note, refs))
    if rating.dimensions["D5"].score >= 4:
        findings.append(mk("D5", "High" if rating.dimensions["D5"].score == 5 else "Medium",
                           rating.dimensions["D5"].note, rating.dimensions["D5"].signals))
    if rating.dimensions["D4"].score >= 4 and rating.action_capable:
        findings.append(mk("D4", "Medium", rating.dimensions["D4"].note, rating.dimensions["D4"].signals))
    if any("mandate" in n.lower() or "No hard rules" in n for n in rating.notes):
        findings.append(mk("MANDATE", "Medium", "; ".join(rating.notes), []))
    if injection_refs:
        findings.append(mk("INJ", "Informational",
                           "Injection-like text present in repository documentation.", injection_refs))

    return findings[: config.FINDINGS_CAP_PER_UNIT]


def assign_ids(all_findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Set sequential F-ids with id first; return the rebuilt list."""
    rebuilt = []
    for i, finding in enumerate(all_findings, 1):
        rebuilt.append({"id": f"F-{i:04d}", **finding})
    return rebuilt


def build_advice(rating: UnitRating) -> List[Dict[str, str]]:
    actions = []
    raised = [f.rf for f in rating.red_flags if f.status == "raised"]
    for rf in raised:
        if rf in ADVICE_HOWTO:
            actions.append({"what": RED_FLAG_LABELS.get(rf, rf), "why": f"red flag {rf} raised",
                            "how": ADVICE_HOWTO[rf]})
    for dim in ("D5", "D4"):
        if rating.dimensions[dim].score >= 4 and dim in ADVICE_HOWTO:
            actions.append({"what": DIMENSION_NAMES[dim], "why": f"{dim}={rating.dimensions[dim].score}",
                            "how": ADVICE_HOWTO[dim]})
    return actions[:5]


# --- leak check ---------------------------------------------------------------------------

def _tokens(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _shingles(text: str, n: int) -> set:
    toks = _tokens(text)
    if len(toks) < n:
        # A line shorter than the window still counts if it has enough tokens to be distinctive.
        return {" ".join(toks)} if len(toks) >= 4 else set()
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def check_no_verbatim(committed_texts: List[str], source_files: Dict[str, str],
                      n: int = config.LEAK_SHINGLE_TOKENS) -> List[str]:
    """Return a list of leak descriptions; empty means clean."""
    source = set()
    for text in source_files.values():
        for line in text.splitlines():
            if len(line.strip()) >= 20:
                source |= _shingles(line, n)
    leaks = []
    for blob in committed_texts:
        hits = _shingles(blob, n) & source
        if hits:
            leaks.append(f"shares {len(hits)} n-gram(s) with source, e.g. '{sorted(hits)[0]}'")
    return leaks


# --- scorecard (Markdown) -----------------------------------------------------------------

def _pill_txt(rating: str) -> str:
    return f"**{rating}**"


def render_scorecard(report: Dict[str, Any]) -> str:
    run = report["run"]
    units = report["units"]
    lines = [
        "---", f"title: \"Agent Drift Scorecard — {run['org']}\"",
        "subtitle: \"Static design review — design evidence, not certification\"",
        f"date: \"{run['generated_at'][:10]}\"", "toc: true", "---", "",
        "## Method and limitations", "", config.DISCLAIMER, "",
        f"- Run id: `{run['run_id']}`  ", f"- Rater commit: `{run.get('tool_commit', 'n/a')}`  ",
        f"- Engine: {run['engine']}  ",
        "",
        "## Summary", "",
        "| Unit | Class | Agency | Mandate | Inherent | Controls | Residual | Confidence | Red flags |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for u in units:
        r = u["ratings"]
        raised = ", ".join(f["rf"] for f in u["red_flags"] if f["status"] == "raised") or "—"
        mandate = "provisional" if u["provisional"] else "confirmed"
        lines.append(
            f"| {u['unit_id']} | {u['classification']} | {r['agency']} | {mandate} | "
            f"{r['inherent']} | {r['control_strength']} | {_pill_txt(r['residual'])} | "
            f"{r['confidence']} | {raised} |")
    lines += ["", "## Per-unit detail", ""]
    for u in units:
        r = u["ratings"]
        lines.append(f"### {u['unit_id']} — {_pill_txt(r['residual'])}")
        lines.append("")
        lines.append("| Dim | Name | Score | Basis |")
        lines.append("|---|---|---|---|")
        for dim in DRIVERS + CONTROLS:
            d = r["dimensions"][dim]
            lines.append(f"| {dim} | {DIMENSION_NAMES[dim]} | {d['score']}/5 | {d['basis']} |")
        lines.append("")
        lines.append("**Red flags:** " + "; ".join(
            f"{f['rf']} {RED_FLAG_LABELS[f['rf']]}: {f['status']}" for f in u["red_flags"]))
        lines.append("")
        if u["findings"]:
            lines.append("**Findings:**")
            for f in u["findings"]:
                lines.append(f"- `{f['id']}` ({f['risk_rating']}) {f['title']}")
            lines.append("")
        if u["advice"]:
            lines.append("**Top advice:**")
            for a in u["advice"]:
                lines.append(f"- {a['what']} — {a['how']}")
            lines.append("")
    return "\n".join(lines)


# --- dashboard (self-contained HTML) ------------------------------------------------------

def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _dashboard_data(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Slim per-unit payload embedded in the dashboard (no code, just scores and advice)."""
    data = []
    for u in report["units"]:
        r = u["ratings"]
        data.append({
            "id": u["unit_id"], "repo": u.get("repo", ""), "cls": u["classification"],
            "res": r["residual"], "conf": r["confidence"], "agency": r["agency"],
            "inh": r["inherent"], "ctl": r["control_strength"], "prov": u["provisional"],
            "dims": {d: r["dimensions"][d]["score"] for d in DRIVERS + CONTROLS},
            "flags": {f["rf"]: f["status"] for f in u["red_flags"]},
            "advice": u.get("advice", []),
        })
    return data


def dashboard_body(report: Dict[str, Any]) -> str:
    """Artifact-ready page content (title, style, markup, script) — no document skeleton."""
    run = report["run"]
    data_json = json.dumps(_dashboard_data(report), ensure_ascii=False)
    tmpl = _DASHBOARD_TMPL
    return (tmpl
            .replace("__ORG__", _esc(run["org"]))
            .replace("__RUNID__", _esc(run["run_id"]))
            .replace("__DATE__", _esc(run["generated_at"][:10]))
            .replace("__ENGINE__", _esc(run.get("engine", "")))
            .replace("__DISCLAIMER__", _esc(config.DISCLAIMER))
            .replace("__DATA__", data_json))


def render_dashboard(report: Dict[str, Any]) -> str:
    """Full standalone HTML document (opens from disk)."""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            + dashboard_body(report) + "</head></html>").replace("</head></html>", "</body></html>")


# Content template: light/dark tokens, summary tiles, filters, and per-agent HITL review.
# Written without f-strings (CSS/JS braces) — placeholders are substituted above.
_DASHBOARD_TMPL = r"""<title>Agent Drift Review</title>
<style>
:root{--bg:#f3f4f6;--surface:#fff;--surface2:#f8f9fb;--ink:#15181d;--muted:#616b7a;--line:#e2e5ea;
--accent:#3257d6;--high:#d4342a;--med:#d98612;--low:#1f9d57;--info:#6b7280;
--s1:#e7f3ec;--s2:#eef4e4;--s3:#fcf4df;--s4:#fbe6d6;--s5:#f8d7d2;--s1i:#1f6b42;--s5i:#9b2820;
--ok:#1f9d57;--okbg:#e7f3ec;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1116;--surface:#171b22;
--surface2:#12161c;--ink:#e7eaef;--muted:#9aa4b2;--line:#272d37;--accent:#7d97f4;--high:#f06a60;
--med:#e6a148;--low:#49c483;--info:#8b95a4;--s1:#173223;--s2:#1e3321;--s3:#332e18;--s4:#3a2a1e;
--s5:#3f241f;--s1i:#7ddca5;--s5i:#f2a69c;--ok:#49c483;--okbg:#173223;color-scheme:dark;}}
:root[data-theme="dark"]{--bg:#0e1116;--surface:#171b22;--surface2:#12161c;--ink:#e7eaef;
--muted:#9aa4b2;--line:#272d37;--accent:#7d97f4;--high:#f06a60;--med:#e6a148;--low:#49c483;
--info:#8b95a4;--s1:#173223;--s2:#1e3321;--s3:#332e18;--s4:#3a2a1e;--s5:#3f241f;--s1i:#7ddca5;
--s5i:#f2a69c;--ok:#49c483;--okbg:#173223;color-scheme:dark;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1020px;margin:0 auto;padding-block:32px 72px;padding-inline:18px}
.eyebrow{font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);
font-family:ui-monospace,Menlo,Consolas,monospace}
h1{font-size:clamp(23px,4vw,32px);margin:.2em 0 .1em;letter-spacing:-.01em}
.lede{color:var(--muted);max-width:64ch;margin:0 0 18px}
.disc{font-size:12.5px;color:var(--muted);background:var(--surface);border:1px solid var(--line);
border-left:3px solid var(--med);border-radius:8px;padding:10px 13px;margin-bottom:20px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:18px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile .n{font-size:24px;font-weight:600;font-variant-numeric:tabular-nums}
.tile .k{font-size:12px;color:var(--muted);margin-top:2px}
.tile.ok .n{color:var(--ok)}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:16px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{border:0;background:var(--surface);color:var(--muted);font:inherit;font-size:12.5px;
padding:6px 11px;cursor:pointer;border-right:1px solid var(--line)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--accent);color:#fff}
.btn{border:1px solid var(--line);background:var(--surface);color:var(--ink);font:inherit;
font-size:12.5px;padding:6px 12px;border-radius:8px;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.grow{flex:1}
.agent{background:var(--surface);border:1px solid var(--line);border-radius:12px;margin-bottom:10px;overflow:hidden}
.head{display:flex;align-items:flex-start;gap:11px;padding:13px 15px;cursor:pointer;min-width:0}
.head:hover{background:var(--surface2)}
.caret{color:var(--muted);transition:transform .15s;flex:none;margin-top:1px}
.agent.open .caret{transform:rotate(90deg)}
.hcontent{flex:1;min-width:0}
.hmain{display:flex;align-items:center;gap:10px}
.name{font-weight:600;min-width:0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.name small{display:block;font-weight:400;color:var(--muted);font-size:11px;
font-family:ui-monospace,Menlo,Consolas,monospace;overflow:hidden;text-overflow:ellipsis}
.hmeta{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:7px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff;flex:none}
.p-High{background:var(--high)}.p-Medium{background:var(--med)}.p-Low{background:var(--low)}.p-Informational{background:var(--info)}
.sugcount{font-size:12px;color:var(--muted);flex:none;font-variant-numeric:tabular-nums}
.badge-appr{background:var(--okbg);color:var(--ok);border-radius:999px;padding:2px 9px;font-size:11.5px;font-weight:600;flex:none}
.rfrow{display:flex;flex-wrap:wrap;gap:3px}
.rf{font-size:10.5px;font-weight:600;padding:2px 5px;border-radius:5px;
background:color-mix(in srgb,var(--muted) 16%,transparent);color:var(--muted);font-family:ui-monospace,Menlo,Consolas,monospace}
.rf.raised{background:var(--high);color:#fff}
.rf.observation{background:color-mix(in srgb,var(--med) 24%,transparent);color:var(--med)}
.body{border-top:1px solid var(--line);padding:14px 15px;display:none}
.agent.open .body{display:block}
.heat{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:14px}
.cellbox{display:flex;flex-direction:column;align-items:center;width:40px}
.cellbox .lab{font-size:10px;color:var(--muted);font-family:ui-monospace,Menlo,Consolas,monospace}
.cellbox .v{width:100%;text-align:center;font-variant-numeric:tabular-nums;font-size:13px;
border-radius:5px;padding:3px 0;margin-top:2px}
.v.c1{background:var(--s1);color:var(--s1i)}.v.c2{background:var(--s2)}.v.c3{background:var(--s3)}
.v.c4{background:var(--s4)}.v.c5{background:var(--s5);color:var(--s5i);font-weight:600}
.mode{font-size:12.5px;border-radius:8px;padding:8px 12px;margin-bottom:16px;border:1px solid var(--line);
background:var(--surface);color:var(--muted)}
.mode.shared{border-left:3px solid var(--low)}
.mode.local{border-left:3px solid var(--med)}
.mode.ro{border-left:3px solid var(--info)}
.sug{border:1px solid var(--line);border-radius:10px;padding:12px 13px;margin-bottom:9px}
.sug.proposed{border-color:var(--ok)}
.sug.accepted{border-color:var(--ok);background:var(--okbg)}
.sug.declined{opacity:.6}
.sug h4{margin:0 0 3px;font-size:14px}
.sug .why{font-size:12px;color:var(--muted);margin:0 0 5px}
.sug .how{font-size:13px;margin:0 0 10px}
.role{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
font-family:ui-monospace,Menlo,Consolas,monospace;margin:0 0 5px}
.sugact{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.sugact .status{font-size:12px;color:var(--muted);margin-left:auto}
.ownerbox{margin-top:10px;padding-top:10px;border-top:1px dashed var(--line);display:none}
.sug.proposed .ownerbox,.sug.accepted .ownerbox,.sug.declined .ownerbox{display:block}
.btnpri{border:1px solid var(--ok);background:transparent;color:var(--ok);font:inherit;font-size:12.5px;
padding:5px 13px;border-radius:8px;cursor:pointer;font-weight:600}
.btnpri.on{background:var(--ok);color:#fff}
.btnq{border:1px solid var(--line);background:transparent;color:var(--muted);font:inherit;
font-size:12.5px;padding:5px 13px;border-radius:8px;cursor:pointer}
.btnq.on{background:var(--muted);color:#fff;border-color:var(--muted)}
.btnbad{border:1px solid var(--high);color:var(--high)}
.btnbad.on{background:var(--high);color:#fff}
.note{font:inherit;font-size:12.5px;padding:5px 9px;border:1px solid var(--line);border-radius:8px;
background:var(--surface2);color:var(--ink);width:100%;margin-top:7px}
.none{color:var(--muted);font-size:13px;font-style:italic}
.leg{color:var(--muted);font-size:12px;margin-top:14px}
.hide{display:none!important}
.btn.demo{border-color:var(--accent);color:var(--accent);font-weight:600}
.spot{outline:3px solid var(--accent);outline-offset:3px;border-radius:10px;
transition:outline-color .2s;animation:pulse 1.4s ease-in-out infinite}
@keyframes pulse{0%,100%{outline-color:var(--accent)}50%{outline-color:color-mix(in srgb,var(--accent) 35%,transparent)}}
@media (prefers-reduced-motion:reduce){.spot{animation:none}}
.caption{position:fixed;left:50%;bottom:calc(18px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);
z-index:50;max-width:min(680px,92vw);background:var(--ink);color:var(--bg);border-radius:12px;
padding:12px 16px;font-size:14px;line-height:1.5;box-shadow:0 6px 24px rgba(0,0,0,.35);
display:flex;align-items:center;gap:10px}
.caption .btn{background:transparent;border-color:color-mix(in srgb,var(--bg) 40%,transparent);color:var(--bg)}
body.demoing{scroll-behavior:smooth}
</style>

<div class="wrap">
  <div class="eyebrow">SAAF · Agent Drift Rater · static design review</div>
  <h1>Agent Drift Review</h1>
  <p class="lede">Every agent's susceptibility to <b>drift</b> — acting outside its approved mandate without anyone changing it. The reviewer <b>approves</b> the suggestions worth acting on; each becomes a fix request the <b>repo owner</b> accepts or declines.</p>
  <div class="disc">__DISCLAIMER__</div>
  <div id="mode" class="mode"></div>

  <div class="tiles" id="tiles"></div>

  <div class="bar">
    <div class="seg" id="filter" role="group" aria-label="Filter by residual rating">
      <button data-f="all" aria-pressed="true">All</button>
      <button data-f="High" aria-pressed="false">High</button>
      <button data-f="Medium" aria-pressed="false">Medium</button>
      <button data-f="Low" aria-pressed="false">Low</button>
    </div>
    <button class="btn" id="onlySug" aria-pressed="false">Only with suggestions</button>
    <button class="btn" id="onlyProposed" aria-pressed="false">Only proposed fixes</button>
    <span class="grow"></span>
    <button class="btn demo" id="demo">▶ Watch demo</button>
    <button class="btn" id="expand">Expand all</button>
    <button class="btn" id="copyPlan">Copy fix requests</button>
    <button class="btn" id="copyIds" title="Copy approved fix ids as JSON for `create-issues --approved`">Copy IDs for issues</button>
  </div>

  <div id="list"></div>

  <div class="leg">Drivers D1–D5 (proxy pressure · self-editing · context loss · untrusted input · permission creep) raise risk; controls C1–C5 (hard rules in code · versioning · independent review · oversight &amp; rollback · replayable log) lower it. Red flags: solid = raised, amber = observation.</div>
  <div class="leg">Workflow: <b>Approve upgrade</b> (reviewer) sends the suggestion to the repo owner. The owner then marks it <b>Will fix</b> or <b>Won't fix</b>. Decisions are shared with everyone who can open this page.</div>
  <div class="leg" id="meta"></div>
</div>

<div class="caption" id="caption" hidden>
  <span id="captext"></span>
  <button class="btn" id="demoStop" aria-label="Stop demo">Stop</button>
</div>

<script>
const DATA = __DATA__;
const RUN = "__RUNID__", ORG = "__ORG__", DATE = "__DATE__";
const DIMS = ["D1","D2","D3","D4","D5","C1","C2","C3","C4","C5"];
const RFS = ["RF1","RF2","RF3","RF4","RF5","RF6"];
const RES_ORDER = {High:0, Medium:1, Low:2, Informational:3};
DATA.sort((a,b)=> (RES_ORDER[a.res]-RES_ORDER[b.res]) || a.id.localeCompare(b.id));
const BY_ID = Object.fromEntries(DATA.map(u=>[u.id,u]));

// Hover explanations for every abbreviation on the page.
const DIM_INFO = {
  D1:"D1 — Proxy pressure: a performance target or KPI in the agent's own context that rewards bending a rule.",
  D2:"D2 — Self-editing: the agent can write its own prompt, memory, or config at runtime.",
  D3:"D3 — Context loss: the approved policy can drop out of context, leaving only a paraphrase.",
  D4:"D4 — Untrusted input: external or user content reaches the agent (prompt-injection surface).",
  D5:"D5 — Permission creep: broad tool access — subprocess, network writes, deletes, bypassed permissions.",
  C1:"C1 — Hard rules in code: limits enforced in code with a test proving the guard blocks, not just in the prompt.",
  C2:"C2 — Versioning: instructions and memory are versioned and diffed against an approved baseline.",
  C3:"C3 — Independent review: tests, evals, a validator, or drift metrics check the behaviour.",
  C4:"C4 — Oversight & rollback: a human approves mandated actions; rollback / quarantine exists.",
  C5:"C5 — Replayable log: each decision records input, instruction & model version, tool calls, outcome.",
};
const RF_INFO = {
  RF1:"RF1 — It can edit itself (prompt/memory/config writable at runtime).",
  RF2:"RF2 — A target in its context (a score that rewards bending a rule).",
  RF3:"RF3 — Rules only in the prompt (hard limits with no code check).",
  RF4:"RF4 — Escalations falling (proxy — not fully observable from static code).",
  RF5:"RF5 — Softening language (its own notes weaken a rule, e.g. 'required' → 'plausible').",
  RF6:"RF6 — No replayable log (a decision can't be traced to its instruction version).",
};
const RES_INFO = {
  High:"High residual drift risk after weighing drivers against controls.",
  Medium:"Medium residual risk.", Low:"Low residual risk.",
  Informational:"Informational — no material drift risk found, or not an action-taking agent.",
};
const AGENCY_INFO = {
  advisory:"Advisory: produces output for a human; takes no actions itself.",
  assisted:"Assisted: takes some actions, with human oversight present.",
  autonomous:"Autonomous: takes actions (tools, writes, network) without a human gate.",
};

function esc(s){ return String(s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
const fixId=(uid,i)=>`${uid}__${i}`;

// ---- shared state (db) with a per-browser fallback -------------------------------------
let DB=null, canWrite=true, mode="local";
const fixes = new Map();                        // fixId -> {decision, ownerNote, ...}
const local = {
  key:id=>`drift:${RUN}:${id}`,
  all(){ const m=new Map(); try{ for(let i=0;i<localStorage.length;i++){ const k=localStorage.key(i);
    if(k.startsWith(`drift:${RUN}:`)) m.set(k.slice(`drift:${RUN}:`.length), JSON.parse(localStorage.getItem(k))); } }catch(e){} return m; },
  set(id,v){ try{ v?localStorage.setItem(this.key(id),JSON.stringify(v)):localStorage.removeItem(this.key(id)); }catch(e){} },
};

let filter="all", onlySug=false, onlyProposed=false;

function tiles(){
  const by={High:0,Medium:0,Low:0,Informational:0};
  let sug=0;
  DATA.forEach(u=>{ by[u.res]=(by[u.res]||0)+1; sug+=(u.advice||[]).length; });
  let proposed=0, accepted=0, declined=0;
  fixes.forEach(f=>{ proposed++; if(f.decision==="accepted")accepted++; else if(f.decision==="declined")declined++; });
  document.getElementById("tiles").innerHTML =
    tile(DATA.length,"agents rated")+
    tile(by.High,"High risk")+
    tile(sug,"suggestions")+
    `<div class="tile ok"><div class="n">${proposed}</div><div class="k">proposed to owners</div></div>`+
    `<div class="tile ok"><div class="n">${accepted}</div><div class="k">owner will fix</div></div>`+
    tile(declined,"owner won't fix");
}
function tile(n,k){ return `<div class="tile"><div class="n">${n}</div><div class="k">${esc(k)}</div></div>`; }

function card(u){
  const flags = RFS.map(r=>{ const st=u.flags[r]; const c=st==="raised"?"rf raised":st==="observation"?"rf observation":"rf";
    return `<span class="${c}" title="${esc(RF_INFO[r])} (${st||"not raised"})">${r}</span>`; }).join("");
  const heat = DIMS.map(d=>`<div class="cellbox" title="${esc(DIM_INFO[d])} Score ${u.dims[d]}/5.">`+
    `<span class="lab">${d}</span><span class="v c${u.dims[d]}">${u.dims[d]}</span></div>`).join("");
  const sugs = (u.advice&&u.advice.length) ? u.advice.map((a,i)=>sugHtml(u,a,i)).join("")
      : `<div class="none">No upgrade suggestions — no red flags or high drivers raised.</div>`;
  const sugN = (u.advice||[]).length;
  return `<div class="agent" data-res="${u.res}" data-sug="${sugN}" data-id="${esc(u.id)}">
    <div class="head" onclick="toggle(this)">
      <span class="caret">▶</span>
      <div class="hcontent">
        <div class="hmain">
          <span class="name">${esc(u.id)}<small title="${esc(AGENCY_INFO[u.agency]||'')}">${esc(u.repo||u.cls)} · ${esc(u.agency)}</small></span>
          <span class="pill p-${u.res}" title="${esc(RES_INFO[u.res]||'')}">${u.res}</span>
        </div>
        <div class="hmeta">
          <span class="rfrow">${flags}</span>
          <span class="sugcount" title="Number of upgrade suggestions for this agent">${sugN} sugg.</span>
        </div>
      </div>
    </div>
    <div class="body">
      <div class="heat" title="Drivers D1–D5 raise drift risk; controls C1–C5 lower it. Hover a cell for its meaning.">${heat}</div>
      ${sugs}
    </div></div>`;
}

function sugHtml(u,a,i){
  const id=fixId(u.id,i);
  return `<div class="sug" data-fix-id="${esc(id)}">
    <p class="role">Reviewer</p>
    <h4>${esc(a.what||"Improvement")}</h4>
    <p class="why">Why: ${esc(a.why||"")}</p>
    <p class="how">${esc(a.how||"")}</p>
    <div class="sugact">
      <button class="btnpri b-appr" onclick="approve('${esc(u.id)}',${i})" title="Send this as a fix request to the repo owner">Approve upgrade</button>
      <span class="status"></span>
    </div>
    <div class="ownerbox">
      <p class="role">Repo owner — decide</p>
      <div class="sugact">
        <button class="btnpri b-fix" onclick="decide('${esc(u.id)}',${i},'accepted')">Will fix</button>
        <button class="btnq btnbad b-no" onclick="decide('${esc(u.id)}',${i},'declined')">Won't fix</button>
      </div>
      <input class="note" placeholder="Owner note (optional) — reason or ticket" onchange="note('${esc(u.id)}',${i},this.value)">
    </div>
  </div>`;
}

function applyFix(el){
  const id=el.dataset.fixId; const f=fixes.get(id);
  const appr=el.querySelector(".b-appr"), status=el.querySelector(".status");
  const fix=el.querySelector(".b-fix"), no=el.querySelector(".b-no"), noteEl=el.querySelector(".note");
  if(!f){ el.className="sug"; appr.classList.remove("on"); appr.textContent="Approve upgrade";
    status.textContent="Not proposed"; fix&&fix.classList.remove("on"); no&&no.classList.remove("on"); return; }
  const dec=f.decision||"pending";
  el.className = "sug "+(dec==="accepted"?"accepted":dec==="declined"?"declined":"proposed");
  appr.classList.add("on"); appr.textContent="Approved ✓";
  status.textContent = dec==="accepted"?"Owner will fix":dec==="declined"?"Owner won't fix":"Proposed to owner";
  fix&&fix.classList.toggle("on", dec==="accepted");
  no&&no.classList.toggle("on", dec==="declined");
  if(noteEl && document.activeElement!==noteEl) noteEl.value = f.ownerNote||"";
}
function applyAll(){ document.querySelectorAll(".sug[data-fix-id]").forEach(applyFix); tiles(); applyFilter(); }

async function approve(uid,i){
  const id=fixId(uid,i), u=BY_ID[uid], a=u.advice[i];
  if(fixes.has(id)){ return unapprove(id); }   // toggle off
  const body={ unit:uid, repo:u.repo||"", residual:u.res, title:a.what||"", why:a.why||"",
    how:a.how||"", redFlag:(a.why||"").replace(/^red flag /,""), decision:"pending", ownerNote:"",
    approvedAt:new Date().toISOString() };
  fixes.set(id, body); applyAll();            // optimistic
  if(DB&&canWrite){ try{ await DB.collection("fixes").doc(id).set(body); }
    catch(e){ if(e&&e.code==="invalid_argument"){ goReadOnly(); } fixes.delete(id); applyAll(); } }
  else { local.set(id, body); }
}
async function unapprove(id){
  fixes.delete(id); applyAll();
  if(DB&&canWrite){ try{ await DB.collection("fixes").doc(id).delete(); }catch(e){} }
  else { local.set(id,null); }
}
async function decide(uid,i,verdict){
  const id=fixId(uid,i); const f=fixes.get(id); if(!f) return;
  const next = f.decision===verdict ? "pending" : verdict;
  const patch={ decision:next, decidedAt:new Date().toISOString() };
  fixes.set(id, Object.assign({}, f, patch)); applyAll();
  if(DB&&canWrite){ try{ await DB.collection("fixes").doc(id).update(patch); }catch(e){} }
  else { local.set(id, fixes.get(id)); }
}
async function note(uid,i,val){
  const id=fixId(uid,i); const f=fixes.get(id); if(!f) return;
  const patch={ ownerNote:String(val||"").slice(0,500) };
  fixes.set(id, Object.assign({}, f, patch));
  if(DB&&canWrite){ try{ await DB.collection("fixes").doc(id).update(patch); }catch(e){} }
  else { local.set(id, fixes.get(id)); }
}
function goReadOnly(){ canWrite=false; setMode("ro"); }

function render(){
  document.getElementById("list").innerHTML = DATA.map(card).join("");
  applyAll();
  document.getElementById("meta").textContent = `${ORG} · run ${RUN} · ${DATE}`;
}
function applyFilter(){
  document.querySelectorAll(".agent").forEach(el=>{
    const okRes = filter==="all" || el.dataset.res===filter;
    const okSug = !onlySug || Number(el.dataset.sug)>0;
    let okProp = true;
    if(onlyProposed){ okProp=false; el.querySelectorAll(".sug[data-fix-id]").forEach(s=>{ if(fixes.has(s.dataset.fixId)) okProp=true; }); }
    el.classList.toggle("hide", !(okRes&&okSug&&okProp));
  });
}
function toggle(head){ head.parentElement.classList.toggle("open"); }

function setMode(m){
  mode=m; const el=document.getElementById("mode");
  el.className="mode "+m;
  el.innerHTML = m==="shared"
    ? "Shared review mode. Approvals and owner decisions are saved for everyone who can open this page."
    : m==="ro"
    ? "Read-only: you can view ratings but not record decisions. Ask the owner for edit access."
    : "Local mode: this page isn't connected to shared storage, so your decisions are saved in this browser only.";
}

function copyPlan(){
  const lines=[`Agent drift — fix requests (${ORG}, run ${RUN})`,""];
  DATA.forEach(u=>{ (u.advice||[]).forEach((a,i)=>{ const f=fixes.get(fixId(u.id,i)); if(!f) return;
    const d=f.decision==="accepted"?"WILL FIX":f.decision==="declined"?"WON'T FIX":"proposed";
    lines.push(`- [${u.id}] (${d}) ${a.what}: ${a.how}`+(f.ownerNote?`  — note: ${f.ownerNote}`:"")); }); });
  if(lines.length===2) lines.push("(no fixes proposed yet)");
  const text=lines.join("\n");
  (navigator.clipboard?navigator.clipboard.writeText(text):Promise.reject()).then(()=>flash("Copied"),()=>fallbackCopy(text));
}
function fallbackCopy(t){ const ta=document.createElement("textarea"); ta.value=t; document.body.appendChild(ta);
  ta.select(); try{document.execCommand("copy"); flash("Copied");}catch(e){flash("Copy failed");} ta.remove(); }
function flash(msg){ const b=document.getElementById("copyPlan"); const o=b.textContent; b.textContent=msg; setTimeout(()=>b.textContent=o,1400); }

// ---- controls --------------------------------------------------------------------------
document.getElementById("filter").addEventListener("click",e=>{
  const b=e.target.closest("button"); if(!b)return; filter=b.dataset.f;
  document.querySelectorAll("#filter button").forEach(x=>x.setAttribute("aria-pressed", x===b)); applyFilter();
});
function toggleBtn(id,set){ const b=document.getElementById(id); b.setAttribute("aria-pressed",set);
  b.style.borderColor=set?"var(--accent)":""; }
document.getElementById("onlySug").addEventListener("click",e=>{ onlySug=!onlySug; toggleBtn("onlySug",onlySug); applyFilter(); });
document.getElementById("onlyProposed").addEventListener("click",e=>{ onlyProposed=!onlyProposed; toggleBtn("onlyProposed",onlyProposed); applyFilter(); });
document.getElementById("expand").addEventListener("click",e=>{
  const open=e.target.textContent.startsWith("Expand");
  document.querySelectorAll(".agent:not(.hide)").forEach(a=>a.classList.toggle("open",open));
  e.target.textContent=open?"Collapse all":"Expand all";
});
document.getElementById("copyPlan").addEventListener("click",copyPlan);
function copyIds(){
  const ids=[]; fixes.forEach((f,id)=>ids.push(id));
  const text=JSON.stringify(ids,null,0);
  (navigator.clipboard?navigator.clipboard.writeText(text):Promise.reject())
    .then(()=>flashBtn("copyIds","Copied JSON"),()=>{ fallbackCopy(text); });
}
function flashBtn(id,msg){ const b=document.getElementById(id); const o=b.textContent; b.textContent=msg; setTimeout(()=>b.textContent=o,1400); }
document.getElementById("copyIds").addEventListener("click",copyIds);

// ---- guided demo with browser voice-over -----------------------------------------------
// ~90 seconds. Narrates each step via the Web Speech API (plays in the viewer's own
// browser after the click) and spotlights the element it is describing. All changes are
// visual only — the demo never writes to the shared store, and resets itself at the end.
let demoOn=false;
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
function demoWait(ms){ return new Promise(r=>setTimeout(r, demoOn?ms:0)); }
// Pick an English voice so the narration is read in English regardless of the viewer's
// system language (otherwise a Dutch default voice reads the English script phonetically).
let enVoice=null;
function pickVoice(){
  try{ const vs=window.speechSynthesis.getVoices()||[];
    enVoice = vs.find(v=>/^en[-_]?US/i.test(v.lang)) || vs.find(v=>/^en[-_]?GB/i.test(v.lang))
      || vs.find(v=>/^en/i.test(v.lang)) || null;
  }catch(e){ enVoice=null; }
}
try{ pickVoice(); if(window.speechSynthesis) window.speechSynthesis.onvoiceschanged=pickVoice; }catch(e){}
function speak(t){ return new Promise(res=>{
  if(!demoOn) return res();
  try{ const sy=window.speechSynthesis; if(!sy) throw 0;
    if(!enVoice) pickVoice();
    const u=new SpeechSynthesisUtterance(t); u.rate=1.02; u.lang="en-US";
    if(enVoice) u.voice=enVoice;
    let done=false; const fin=()=>{ if(!done){ done=true; res(); } };
    u.onend=fin; u.onerror=fin; sy.cancel(); sy.speak(u);
    setTimeout(fin, Math.max(3500, t.length*60)+1500);   // safety net if speech never ends
  }catch(e){ setTimeout(res, Math.max(2600, t.length*45)); }   // no speech: pace by length
}); }
function caption(t){ document.getElementById("captext").textContent=t; }
function spot(el){ document.querySelectorAll(".spot").forEach(x=>x.classList.remove("spot"));
  if(el){ el.classList.add("spot"); el.scrollIntoView({behavior:reduce?"auto":"smooth", block:"center"}); } }
async function dstep(text, act){ if(!demoOn) throw 0; caption(text); if(act) act(); await speak(text); await demoWait(450); }

async function runDemo(){
  if(demoOn) return; demoOn=true; document.body.classList.add("demoing");
  document.getElementById("caption").hidden=false;
  const agent = DATA.find(u=>u.res==="High" && (u.advice||[]).length>=2) || DATA.find(u=>(u.advice||[]).length) || DATA[0];
  const el = ()=>document.querySelector(`.agent[data-id="${CSS.escape(agent.id)}"]`);
  try{
    await dstep("This dashboard rates every SAAF agent for drift — when an agent acts outside its approved rules without anyone changing them.", ()=>spot(document.getElementById("tiles")));
    await dstep("Each row is one agent. The coloured pill on the right is its overall drift rating: High, Medium, or Low.", ()=>spot(el().querySelector(".pill")));
    await dstep("The red R F chips are the six warning signs. R F 3, for example, means the agent's hard rules live only in the prompt, with no check in code.", ()=>spot(el().querySelector(".rfrow")));
    if(!el().classList.contains("open")) el().classList.add("open"); await demoWait(500);
    await dstep("Opening an agent shows ten scores. D 1 to D 5 are drift drivers that raise risk; C 1 to C 5 are controls that lower it. Hover any cell to read what it means.", ()=>spot(el().querySelector(".heat")));
    const sug = el().querySelector(".sug");
    await dstep("Underneath are the suggestions that would improve the rating. As the reviewer, you approve the ones worth doing.", ()=>spot(sug));
    const appr=sug.querySelector(".b-appr"); appr.classList.add("on"); appr.textContent="Approved ✓";
    sug.classList.add("proposed"); sug.querySelector(".status").textContent="Proposed to owner (demo)";
    await dstep("Approving turns the suggestion into a fix request and sends it to the repository owner.", ()=>spot(sug.querySelector(".sugact")));
    const fix=sug.querySelector(".b-fix"); if(fix) fix.classList.add("on");
    sug.classList.remove("proposed"); sug.classList.add("accepted");
    sug.querySelector(".status").textContent="Owner will fix (demo)";
    await dstep("The owner opens the same page and decides: Will fix, or Won't fix, with an optional note — and that decision is shared back to everyone.", ()=>spot(sug.querySelector(".ownerbox")));
    await dstep("That's the loop: rate every agent, approve the fixes that matter, and let each owner decide. Thanks for watching.", ()=>spot(document.getElementById("tiles")));
  }catch(e){}
  endDemo(true);
}
function endDemo(reset){
  demoOn=false; document.body.classList.remove("demoing");
  try{ window.speechSynthesis && window.speechSynthesis.cancel(); }catch(e){}
  document.getElementById("caption").hidden=true;
  document.querySelectorAll(".spot").forEach(x=>x.classList.remove("spot"));
  if(reset) applyAll();   // undo the demo's visual-only button/status changes
}
document.getElementById("demo").addEventListener("click",runDemo);
document.getElementById("demoStop").addEventListener("click",()=>endDemo(true));

// ---- boot ------------------------------------------------------------------------------
render();
(async ()=>{
  try{
    const C=window.claude;
    if(C&&C.use){
      const [db,user]=await Promise.all([C.use("db"), C.use("user").catch(()=>null)]);
      if(db){ DB=db; setMode("shared");
        if(user){ try{ const w=user.can&&user.can("data.write"); if(w===false) goReadOnly(); }catch(e){} }
        db.collection("fixes").onSnapshot(snap=>{
          fixes.clear(); snap.docs.forEach(d=>{ if(d.exists) fixes.set(d.id, d.data()); }); applyAll();
        }, err=>{ if(err&&(err.code==="revoked"||err.code==="not_granted")) { DB=null; setMode("local"); loadLocal(); } });
        return;
      }
    }
    setMode("local"); loadLocal();
  }catch(e){ setMode("local"); loadLocal(); }
})();
function loadLocal(){ fixes.clear(); local.all().forEach((v,k)=>{ if(v) fixes.set(k,v); }); applyAll(); }
</script>"""
