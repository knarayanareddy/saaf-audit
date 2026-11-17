"""Local web UI for the joiners-movers-leavers agent.

Runs on 127.0.0.1 only. One review at a time, held in memory; every step is also
written to a run folder under runs/ (inputs, results, model input and output,
sign-off, and an append-only log), so a session can be reconstructed afterwards.

Start it with:  python3 run.py   (or double-click "Start Demo.command" on a Mac)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ai.claude_runner import DEFAULT_TIMEOUT, claude_status, draft_findings
from engine.jml_checks import ENGINE_VERSION, public_review, run_review
from engine.pseudonymise import Pseudonymiser, build_payload
from engine.sources import DEFAULT_SOURCES, load_sources

log = logging.getLogger("jml.web")

REPO_ROOT = Path(__file__).parents[1]
WEB_DIR = Path(__file__).parent
RUNS_DIR = REPO_ROOT / "runs"
SOURCES_PATH = Path(os.environ.get("JML_SOURCES", str(DEFAULT_SOURCES)))
DRAFT_MODE = os.environ.get("JML_DRAFT_MODE", "auto")  # auto | prepared | deterministic
I18N = {lang: json.loads((WEB_DIR / "i18n" / f"{lang}.json").read_text(encoding="utf-8")) for lang in ("en", "nl")}
LOGO_SVG = (WEB_DIR / "static" / "brand" / "logo-saaf.svg").read_text(encoding="utf-8")
# Changes whenever a static file changes, so browsers never run a stale script after an update.
ASSET_VERSION = str(max(int(f.stat().st_mtime) for f in (WEB_DIR / "static").rglob("*") if f.is_file()))

app = FastAPI(title="Joiners-movers-leavers agent", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

STATE: dict = {"sources": None, "review": None, "draft": None, "signoff": None, "run_dir": None,
               "claude": None, "claude_checked": 0.0}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(kind: str, **data: object) -> None:
    """Append one line to the run's audit log."""
    run_dir: Optional[Path] = STATE["run_dir"]
    if run_dir is None:
        return
    with open(run_dir / "events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": _now(), "event": kind, **data}, ensure_ascii=False) + "\n")


def _save(name: str, data: object) -> None:
    if STATE["run_dir"] is not None:
        (STATE["run_dir"] / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _preview() -> dict:
    """Source names and files from the config, without reading the data (shown before loading)."""
    cfg = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    policy = json.loads((SOURCES_PATH.parent / cfg["policy"]).read_text(encoding="utf-8"))
    rows = [{"key": "hr", "label": "HR employee master data", "file": Path(cfg["hr"]).name},
            {"key": "accounts", "label": cfg["directory"].get("label", "Directory accounts"),
             "file": Path(cfg["directory"]["accounts"]).name}]
    rows += [{"key": f"system:{s['name']}", "label": s.get("label", s["name"]), "file": Path(s["entitlements"]).name}
             for s in cfg["systems"]]
    rows.append({"key": "tickets", "label": cfg["tickets"].get("label", "Tickets"), "file": Path(cfg["tickets"]["file"]).name})
    rows.append({"key": "policy", "label": "Access policy and role model", "file": Path(cfg["policy"]).name})
    return {"organisation": policy.get("organisation", ""), "audit_period": policy["audit_period"],
            "extraction_date": policy["extraction_date"], "sources": rows}


def _require(key: str, step: str) -> object:
    if STATE[key] is None:
        raise HTTPException(status_code=409, detail=f"Run the {step} step first.")
    return STATE[key]


@app.get("/", response_class=HTMLResponse)
def index(request: Request, lang: Optional[str] = None, theme: str = "light") -> HTMLResponse:
    language = lang if lang in I18N else "en"
    app_cfg = {"lang": language, "lang_from_url": lang in I18N, "preview": _preview(), "mode": DRAFT_MODE,
               "expected_seconds": 40}
    return templates.TemplateResponse(request, "index.html", {
        "lang": language, "theme": "dark" if theme == "dark" else "light", "i18n": I18N, "app": app_cfg,
        "logo_svg": LOGO_SVG, "version": ENGINE_VERSION, "v": ASSET_VERSION})


@app.get("/api/status")
def status() -> dict:
    if STATE["claude"] is None or time.monotonic() - STATE["claude_checked"] > 30:
        STATE["claude"] = claude_status()
        STATE["claude_checked"] = time.monotonic()
    return STATE["claude"]


@app.post("/api/load")
def load() -> dict:
    src = load_sources(SOURCES_PATH)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{stamp}-ui"
    run_dir.mkdir(parents=True, exist_ok=True)
    STATE.update(sources=src, review=None, draft=None, signoff=None, run_dir=run_dir)
    _event("sources_loaded", config=str(SOURCES_PATH), fingerprint=src.fingerprint(), sources=src.summaries())
    pol = src.policy
    return {"organisation": pol.get("organisation", ""), "audit_period": pol["audit_period"],
            "extraction_date": pol["extraction_date"], "fingerprint": src.fingerprint(), "name": src.name,
            "sources": src.summaries()}


@app.post("/api/run")
def run() -> dict:
    src = _require("sources", "load")
    review = run_review(src)
    STATE.update(review=review, draft=None, signoff=None)
    pub = public_review(review)
    _save("review_local.json", pub)
    pz = Pseudonymiser(review["_anon_map"], review["_people"])
    _save("model_input.json", build_payload(review, pz))
    _event("tests_run", engine_version=ENGINE_VERSION, exceptions=len(review["exceptions"]),
           by_test={t["id"]: t["exceptions"] for t in review["tests"]})
    return pub


@app.get("/api/model-input")
def model_input() -> dict:
    review = _require("review", "controls")
    return build_payload(review, Pseudonymiser(review["_anon_map"], review["_people"]))


class DraftRequest(BaseModel):
    lang: str = "en"
    mode: str = "auto"


@app.post("/api/draft")
def draft(req: DraftRequest) -> dict:
    review = _require("review", "controls")
    mode = req.mode if req.mode in ("auto", "prepared", "deterministic") else "auto"
    _event("draft_requested", lang=req.lang, mode=mode)
    res = draft_findings(review, STATE["run_dir"], language=req.lang if req.lang in I18N else "en", mode=mode,
                         timeout=DEFAULT_TIMEOUT)
    pz = Pseudonymiser(review["_anon_map"], review["_people"])
    reveal_fields = ("title", "control_objective", "observation", "root_cause", "impact", "recommendation")
    res["findings_display"] = [{**f, **{k: pz.reveal(f[k]) for k in reveal_fields if k in f}} for f in res["findings"]]
    res["assessments_display"] = [{**a, "rationale": pz.reveal(a.get("rationale", "")),
                                   "follow_up": pz.reveal(a.get("follow_up", ""))} for a in res["assessments"]]
    res["summary_display"] = pz.reveal(res.get("summary", ""))
    STATE.update(draft=res, signoff=None)
    _event("draft_returned", mode=res["mode"], model=res.get("model"), duration_s=res.get("duration_s"),
           error=res.get("error"), checks=res["checks"])
    return res


class SignoffRequest(BaseModel):
    reviewer: str
    statement: str


@app.post("/api/signoff")
def signoff(req: SignoffRequest) -> dict:
    d = _require("draft", "findings")
    if len(req.reviewer.strip()) < 2:
        raise HTTPException(status_code=422, detail="Reviewer name is required.")
    now = datetime.now(timezone.utc)
    so = {"reviewer": req.reviewer.strip(), "statement": req.statement,
          "signed_at": now.strftime("%Y-%m-%d %H:%M UTC"), "signed_at_iso": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
          "draft_mode": d["mode"], "fingerprint": STATE["review"]["fingerprint"],
          "findings": [f["id"] for f in d["findings"]]}
    STATE["signoff"] = so
    _save("signoff.json", so)
    _event("signed_off", **so)
    return so


RISKS = ["High", "Medium", "Low", "Informational"]
LIFECYCLES = ["joiner", "mover", "leaver", "baseline"]


def _report_stats(review: dict, draft: Optional[dict]) -> dict:
    """Counts for the executive summary: risk totals, lifecycle x risk heat map, findings by risk."""
    lc_of = {x["id"]: x["lifecycle"] for x in review["tests"]}
    exceptions = review["exceptions"]
    heat = {lc: {r: 0 for r in RISKS} for lc in LIFECYCLES}
    for e in exceptions:
        heat[lc_of.get(e["test_id"], "baseline")][e["risk_rating"]] += 1
    findings = draft["findings"] if draft else []
    return {
        "risks": RISKS,
        "lifecycles": LIFECYCLES,
        "heat": heat,
        "lc_totals": {lc: sum(heat[lc].values()) for lc in LIFECYCLES},
        "exc_by_risk": {r: sum(1 for e in exceptions if e["risk_rating"] == r) for r in RISKS},
        "fnd_by_risk": {r: sum(1 for f in findings if f["risk_rating"] == r) for r in RISKS},
        "exceptions": len(exceptions),
        "findings": len(findings),
        "tests_total": len(review["tests"]),
        "tests_with_exceptions": sum(1 for x in review["tests"] if x["exceptions"]),
        "people": review["population"]["people"],
        "exc_by_id": {e["id"]: e for e in exceptions},
        "lc_of": lc_of,
        "follow_up": sum(1 for a in (draft or {}).get("assessments", []) if a.get("conclusion") == "Needs follow-up"),
    }


@app.get("/report", response_class=HTMLResponse)
def report(request: Request, lang: str = "en") -> HTMLResponse:
    review = _require("review", "controls")
    language = lang if lang in I18N else "en"
    strings = I18N[language]

    def t(key: str, **params: object) -> str:
        s = strings.get(key) or I18N["en"].get(key) or key
        for k, v in params.items():
            s = s.replace("{" + k + "}", str(v))
        return s

    def summary(e: dict) -> str:
        key = "summary." + e["test_id"]
        if key not in strings:
            return e["summary"]
        s = strings[key]
        for k, v in e.get("params", {}).items():
            s = s.replace("{" + k + "}", str(v))
        return s

    html = templates.TemplateResponse(request, "report.html", {
        "lang": language, "t": t, "summary": summary, "review": public_review(review), "draft": STATE["draft"],
        "signoff": STATE["signoff"], "stats": _report_stats(review, STATE["draft"]), "logo_svg": LOGO_SVG,
        "version": ENGINE_VERSION, "v": ASSET_VERSION,
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    _event("report_viewed", lang=language, signed=STATE["signoff"] is not None)
    return html
