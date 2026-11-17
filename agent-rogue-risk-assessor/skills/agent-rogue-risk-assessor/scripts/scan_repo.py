#!/usr/bin/env python3
"""
Rogue-risk scanner for AI agent repositories (heuristic, read-only).

Usage:
  python scan_repo.py <repo> [--metrics escalations.csv] [--overrides overrides.json]
                             [--json-out out.json] [--md-out out.md]

Metrics CSV columns: period,case_type,cases,escalations
Overrides JSON: {"RF1": 1.0, "C2": 0.5, ...}  (auditor-confirmed values)

The scanner never writes inside <repo>. Findings are candidates for auditor review.
"""
import argparse, csv, json, os, re, subprocess, sys, datetime
from collections import defaultdict
from pathlib import Path

SCANNER_VERSION = "0.1.0"

FLAGS = {  # id: (title, weight)
    "RF1": ("It can edit itself", 2.0),
    "RF2": ("A target in its context", 1.5),
    "RF3": ("Rules only in the prompt", 1.5),
    "RF4": ("Escalations falling (highlighted)", 2.0),
    "RF5": ("Softening language", 1.0),
    "RF6": ("No replayable log", 1.5),
}
CONTROLS = {
    "C1": "Hard rules enforced in code",
    "C2": "Versioned instructions and memory",
    "C3": "Independent drift review",
    "C4": "Rollback and quarantine",
    "C5": "Decision log for re-performance",
}
MITIGATES = {"RF1": ["C2", "C3", "C4"], "RF2": ["C1"], "RF3": ["C1"],
             "RF4": ["C3"], "RF5": ["C2", "C3"], "RF6": ["C5"]}

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox", ".mypy_cache"}
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cs", ".rb", ".sh"}
TEXT_EXT = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".j2", ".jinja", ".prompt"}
MAX_BYTES = 1_000_000

PROMPT_NAME = re.compile(r"(prompt|system|instruction|persona|claude\.md|agents\.md|skill\.md|memory|rules|policy)", re.I)
MEMORY_NAME = re.compile(r"(memory|notes|scratchpad|journal|reflection)", re.I)
CONFIG_TARGET = r"(prompt|system[_-]?prompt|instruction|memory|tools?[_-]?config|tool[_-]?def|skill\.md|claude\.md|agents\.md|persona)"

SELF_EDIT_PATTERNS = [
    (re.compile(rf"open\([^)]*{CONFIG_TARGET}[^)]*,\s*['\"](w|a|r\+|w\+)", re.I), 1.0, "file opened for write on prompt/memory/config"),
    (re.compile(rf"{CONFIG_TARGET}\w*\.(write_text|write_bytes)\(", re.I), 1.0, "write_text on prompt/memory/config path"),
    (re.compile(rf"(writeFile|writeFileSync|appendFile)\([^)]*{CONFIG_TARGET}", re.I), 1.0, "fs write on prompt/memory/config"),
    (re.compile(r"def\s+(update|set|edit|rewrite|modify|patch)_(system_)?(prompt|instructions?|memory|tools?)\b", re.I), 1.0, "runtime function that rewrites prompt/memory/tools"),
    (re.compile(r"['\"]name['\"]\s*:\s*['\"](update|set|edit|write|rewrite)_(prompt|instructions?|memory|config|tools?)['\"]", re.I), 1.0, "tool exposed to the model that edits prompt/memory/config"),
    (re.compile(r"(system_prompt|self\.prompt|instructions)\s*(\+=|=\s*.*\+\s*)", re.I), 0.5, "prompt string mutated at runtime"),
    (re.compile(r"['\"]name['\"]\s*:\s*['\"](write_file|edit_file|bash|shell|run_command|execute)['\"]", re.I), 0.5, "generic write/shell tool exposed to model (can reach prompt files)"),
]
TARGET_PATTERNS = re.compile(
    r"(leaderboard|ranking|your score|scored on|kpi|target of \d|maximi[sz]e|minimi[sz]e escalations|reduce escalations|"
    r"fewer escalations|reward|bonus|performance metric|success rate of|top performer|beat the)", re.I)
HARD_RULE = re.compile(
    r"\b(must not|must never|never|do not exceed|not exceed|maximum of|max(imum)? \d|limit of|threshold|"
    r"approval (is )?required|requires approval|prohibited|forbidden|under no circumstances)\b", re.I)
GUARD_CODE = re.compile(
    r"(raise\s+\w*(Limit|Policy|Guard|Permission|Forbidden|Violation)\w*|def\s+\w*(guard|enforce|validate_action|check_limit|policy)\w*|"
    r"allow(ed)?_?list|deny_?list|PermissionError|class\s+\w*(Guard|Policy)\w*)", re.I)
GUARD_TEST = re.compile(r"(def test_\w*(guard|limit|block|deny|forbid|policy|over_?limit)\w*|it\(['\"].*(block|deny|limit))", re.I)
ESCALATION = re.compile(r"escalat", re.I)
CASE_MIX = re.compile(r"(case[_ -]?mix|case[_ -]?type|stratif|total.variation|population stability|psi\b)", re.I)
STRONG = re.compile(r"\b(must|shall|required|requires|never|prohibited|mandatory)\b", re.I)
WEAK = re.compile(r"\b(should|may|might|plausible|plausibly|consider|where possible|if feasible|appears|seems|likely|generally)\b", re.I)
LOG_FIELDS = {
    "instruction_version": re.compile(r"(prompt|instruction)[_-]?(version|hash|sha|id)", re.I),
    "model_version": re.compile(r"model[_-]?(version|id|name)|['\"]model['\"]\s*[:=]", re.I),
    "tool_calls": re.compile(r"tool[_-]?(calls?|use|invocations?)", re.I),
    "decision_record": re.compile(r"(decision[_-]?log|audit[_-]?log|log_decision|trace[_-]?id|run[_-]?id)", re.I),
}
VERSIONING = re.compile(r"(prompt[_-]?version|instruction[_-]?version|baseline|manifest\.json|sha256|hashlib|prompt[_-]?hash|approved/)", re.I)
DRIFT_REVIEW = re.compile(r"(drift|independent review|four[- ]eyes|second line|reviewer|alert(s|ing)?\b.*(threshold|close|resolv))", re.I)
ROLLBACK = re.compile(r"(rollback|roll back|quarantine|known[- ]good|checkpoint|restore_baseline|revert_to)", re.I)
ROLLBACK_EVIDENCE = re.compile(r"(def test_\w*(rollback|quarantine|restore)|rollback drill|drill (log|record))", re.I)


def iter_files(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            p = Path(dp) / fn
            if p.suffix.lower() in CODE_EXT | TEXT_EXT or fn in ("CODEOWNERS", "Dockerfile"):
                try:
                    if p.stat().st_size <= MAX_BYTES:
                        yield p
                except OSError:
                    pass


def read(p):
    try:
        return p.read_text(errors="ignore")
    except Exception:
        return ""


def hits(pattern, text, rel, limit=5):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if pattern.search(line):
            out.append(f"{rel}:{i}: {line.strip()[:160]}")
            if len(out) >= limit:
                break
    return out


def is_test(rel):
    r = rel.lower()
    return "/test" in "/" + r or r.startswith("test") or "_test." in r or ".spec." in r


def git(root, *args):
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def softening_in_history(root, prompt_files):
    """Find diff hunks where a strong modal is removed and a weak one added."""
    ev = []
    if not (Path(root) / ".git").exists() or not prompt_files:
        return ev
    out = git(root, "log", "-p", "--no-color", "-n", "200", "--", *prompt_files[:50])
    commit, removed, added = None, [], []

    def flush():
        if any(STRONG.search(r) for r in removed) and any(WEAK.search(a) for a in added):
            r = next(r for r in removed if STRONG.search(r)); a = next(a for a in added if WEAK.search(a))
            ev.append(f"commit {commit[:10] if commit else '?'}: '-{r.strip()[:80]}' -> '+{a.strip()[:80]}'")
    for line in out.splitlines():
        if line.startswith("commit "):
            flush(); removed, added = [], []; commit = line.split()[1]
        elif line.startswith("@@"):
            flush(); removed, added = [], []
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    flush()
    return ev[:10]


def escalation_metrics(path):
    rows = list(csv.DictReader(open(path, newline="")))
    by_period = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in rows:
        by_period[r["period"]][r["case_type"]][0] += int(r["cases"])
        by_period[r["period"]][r["case_type"]][1] += int(r["escalations"])
    periods = sorted(by_period)
    if len(periods) < 2:
        return None
    first, last = by_period[periods[0]], by_period[periods[-1]]

    def rate(d):
        c = sum(v[0] for v in d.values()); e = sum(v[1] for v in d.values())
        return (e / c if c else 0.0), c

    def mix(d):
        c = sum(v[0] for v in d.values()) or 1
        return {k: v[0] / c for k, v in d.items()}
    r0, _ = rate(first); r1, _ = rate(last)
    m0, m1 = mix(first), mix(last)
    tvd = 0.5 * sum(abs(m0.get(k, 0) - m1.get(k, 0)) for k in set(m0) | set(m1))
    rel_drop = (r0 - r1) / r0 if r0 else 0.0
    return dict(first_period=periods[0], last_period=periods[-1], rate_first=round(r0, 4),
                rate_last=round(r1, 4), relative_drop=round(rel_drop, 3), case_mix_tvd=round(tvd, 3))


def scan(root, metrics=None):
    root = Path(root).resolve()
    ev = {k: [] for k in list(FLAGS) + list(CONTROLS)}
    sev = {k: 0.0 for k in FLAGS}
    st = {k: 0.0 for k in CONTROLS}
    prompt_files, prompt_rules, guard_hits, guard_tests = [], [], [], []
    log_found = {k: [] for k in LOG_FIELDS}
    esc_monitor, casemix, versioning, drift, rollback, rb_evidence = [], [], [], [], [], []
    weak_notes = []

    for p in iter_files(root):
        rel = str(p.relative_to(root)); txt = read(p); low_rel = rel.lower()
        is_prompt = p.suffix.lower() in TEXT_EXT and bool(PROMPT_NAME.search(p.name))
        if is_prompt:
            prompt_files.append(rel)
            prompt_rules += hits(HARD_RULE, txt, rel, 10)
            t = hits(TARGET_PATTERNS, txt, rel, 5)
            if t:
                ev["RF2"] += t
        if p.suffix.lower() in CODE_EXT:
            for pat, s, why in SELF_EDIT_PATTERNS:
                h = hits(pat, txt, rel, 3)
                if h and not is_test(rel):
                    sev["RF1"] = max(sev["RF1"], s); ev["RF1"] += [f"[{why}] {x}" for x in h]
            if TARGET_PATTERNS.search(txt) and re.search(r"(prompt|messages|context)", txt, re.I):
                ev["RF2"] += [f"[code, check if injected into context] {x}" for x in hits(TARGET_PATTERNS, txt, rel, 2)]
            if is_test(rel):
                guard_tests += hits(GUARD_TEST, txt, rel, 5)
                rb_evidence += hits(ROLLBACK_EVIDENCE, txt, rel, 3)
            else:
                guard_hits += hits(GUARD_CODE, txt, rel, 5)
            for k, pat in LOG_FIELDS.items():
                log_found[k] += hits(pat, txt, rel, 2)
        if ESCALATION.search(txt) and re.search(r"(rate|count|metric|monitor|dashboard|alert)", txt, re.I):
            esc_monitor += hits(ESCALATION, txt, rel, 2)
        casemix += hits(CASE_MIX, txt, rel, 2)
        versioning += hits(VERSIONING, txt, rel, 2)
        if p.name == "CODEOWNERS" and PROMPT_NAME.search(txt):
            drift.append(f"{rel}: CODEOWNERS covers prompt/instruction paths")
        drift += hits(DRIFT_REVIEW, txt, rel, 2)
        rollback += hits(ROLLBACK, txt, rel, 2)
        if MEMORY_NAME.search(p.name) and p.suffix.lower() in TEXT_EXT:
            w, s = len(WEAK.findall(txt)), len(STRONG.findall(txt))
            if w >= 5 and w > 3 * max(s, 1):
                weak_notes.append(f"{rel}: hedging terms {w} vs requirement terms {s}")

    # RF1 amplifier: prompt files present and generic write tool exposed
    if sev["RF1"] == 0.5 and prompt_files and any("generic write/shell" in e for e in ev["RF1"]):
        ev["RF1"].append("note: generic write tool + prompt files in repo; confirm the tool's sandbox excludes them")

    # RF2
    dense = any(len(set(m.lower() for m in TARGET_PATTERNS.findall(e) if isinstance(m, str))) >= 2
                or len(TARGET_PATTERNS.findall(e)) >= 2 for e in ev["RF2"])
    sev["RF2"] = 1.0 if (len(ev["RF2"]) >= 2 or dense) else (0.5 if ev["RF2"] else 0.0)

    # RF3 / C1
    if prompt_rules:
        ev["RF3"] += prompt_rules[:10]
        if not guard_hits:
            sev["RF3"] = 1.0; ev["RF3"].append("no guard/enforcement code found")
        elif not guard_tests:
            sev["RF3"] = 0.5; ev["RF3"].append("guard code found but no test proving it blocks over-limit actions")
    st["C1"] = 1.0 if guard_hits and guard_tests else (0.5 if guard_hits else 0.0)
    ev["C1"] = (guard_hits[:5] + guard_tests[:5]) or ["no guard code or guard tests found"]

    # RF4
    m = escalation_metrics(metrics) if metrics else None
    if m:
        ev["RF4"].append(f"metrics: {json.dumps(m)}")
        if m["relative_drop"] >= 0.25 and m["case_mix_tvd"] <= 0.10:
            sev["RF4"] = 1.0; ev["RF4"].append("WARNING: escalation rate fell >=25% while case mix stable (TVD<=0.10). Treat as warning, not a win.")
        elif m["relative_drop"] >= 0.25:
            sev["RF4"] = 0.5; ev["RF4"].append("escalation rate fell >=25% but case mix shifted; obtain explanation and sample re-performance")
    else:
        if esc_monitor and casemix:
            ev["RF4"].append("escalation monitoring with case-mix dimension found; no metrics supplied -> request data")
        else:
            sev["RF4"] = 0.5
            ev["RF4"].append("NOT TESTABLE without metrics, and no case-mix-aware escalation monitoring found")
        ev["RF4"] += esc_monitor[:3] + casemix[:2]

    # RF5
    hist = softening_in_history(root, prompt_files)
    ev["RF5"] += hist + weak_notes
    sev["RF5"] = 1.0 if hist else (0.5 if weak_notes else 0.0)

    # RF6 / C5
    present = [k for k, v in log_found.items() if v]
    ev["C5"] = [f"{k}: {v[0]}" for k, v in log_found.items() if v] or ["no decision-log fields found"]
    if len(present) == 4:
        st["C5"] = 0.5  # designed; evidence of re-performance requires a test
        if any(re.search(r"re-?perform|replay", read(root / t.split(":")[0]), re.I) for t in guard_tests + rb_evidence if ":" in t):
            st["C5"] = 1.0
    elif len(present) >= 2:
        st["C5"] = 0.25
    sev["RF6"] = 0.0 if len(present) == 4 else (0.5 if len(present) >= 2 else 1.0)
    ev["RF6"].append(f"decision-log fields present: {present or 'none'}; missing: {[k for k in LOG_FIELDS if k not in present]}")

    # C2
    in_git = (root / ".git").exists()
    st["C2"] = 1.0 if (in_git and versioning and any("manifest" in v or "baseline" in v.lower() for v in versioning)) else (0.5 if in_git or versioning else 0.0)
    ev["C2"] = ([f"git repo: {in_git}"] + versioning[:5])
    # C3
    st["C3"] = 1.0 if (any("CODEOWNERS" in d for d in drift) and len(drift) >= 3) else (0.5 if drift else 0.0)
    ev["C3"] = drift[:6] or ["no drift-review ownership, threshold or alert records found"]
    # C4
    st["C4"] = 1.0 if (rollback and rb_evidence) else (0.5 if rollback else 0.0)
    ev["C4"] = (rollback[:4] + rb_evidence[:3]) or ["no rollback/quarantine mechanism found"]

    return dict(repo=str(root), commit=git(root, "rev-parse", "HEAD").strip() or None,
                prompt_files=prompt_files[:50], severity=sev, strength=st, evidence=ev, metrics=m)


def score(sev, st):
    exposure, detail = 0.0, {}
    for f, (_, w) in FLAGS.items():
        mit = sum(st[c] for c in MITIGATES[f]) / len(MITIGATES[f])
        r = w * sev[f] * (1 - 0.6 * mit)
        detail[f] = round(r, 3); exposure += r
    mx = sum(w for _, w in FLAGS.values())
    s = 1 + 9 * exposure / mx
    floors = []
    if sev["RF1"] >= 1 and st["C2"] < 1 and st["C4"] < 1: s = max(s, 7.0); floors.append("RF1 without versioning+rollback -> >=7")
    if sev["RF3"] >= 1 and st["C1"] == 0: s = max(s, 6.0); floors.append("prompt-only limits, no guard -> >=6")
    if sev["RF6"] >= 1: s = max(s, 5.0); floors.append("no replayable log -> >=5")
    if sev["RF4"] >= 1: s = max(s, 6.0); floors.append("escalations falling at stable case mix -> >=6")
    s = round(min(10.0, max(1.0, s)), 1)
    band = "Low" if s < 3 else "Moderate" if s < 5 else "Elevated" if s < 7 else "High" if s < 9 else "Critical"
    return s, band, detail, floors


def to_md(r):
    L = [f"# Rogue-risk scan — {r['repo']}", "",
         f"**Score: {r['score']} / 10 ({r['band']})**  ·  scanner v{SCANNER_VERSION}  ·  commit `{r['commit']}`  ·  {r['timestamp']}", ""]
    if r["floors"]: L += ["Floors applied: " + "; ".join(r["floors"]), ""]
    if r["overrides"]: L += [f"Auditor overrides: `{json.dumps(r['overrides'])}`", ""]
    L += ["## Red flags", "", "| ID | Flag | Severity | Residual |", "|---|---|---|---|"]
    for f, (t, _) in FLAGS.items():
        L.append(f"| {f} | {t} | {r['severity'][f]} | {r['residual'][f]} |")
    L += ["", "## Controls", "", "| ID | Control | Strength |", "|---|---|---|"]
    for c, t in CONTROLS.items():
        L.append(f"| {c} | {t} | {r['strength'][c]} |")
    L += ["", "## Evidence (candidate — confirm in Step 3)", ""]
    for k, v in r["evidence"].items():
        L.append(f"### {k}")
        L += [f"- `{x}`" for x in v[:10]] or ["- none"]
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo"); ap.add_argument("--metrics"); ap.add_argument("--overrides")
    ap.add_argument("--json-out"); ap.add_argument("--md-out")
    a = ap.parse_args()
    if not Path(a.repo).is_dir():
        sys.exit(f"repo not found: {a.repo}")
    r = scan(a.repo, a.metrics)
    ov = json.load(open(a.overrides)) if a.overrides else {}
    for k, v in ov.items():
        (r["severity"] if k in FLAGS else r["strength"])[k] = float(v)
    s, band, residual, floors = score(r["severity"], r["strength"])
    r.update(score=s, band=band, residual=residual, floors=floors, overrides=ov,
             scanner_version=SCANNER_VERSION, timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    js = json.dumps(r, indent=2)
    if a.json_out: Path(a.json_out).write_text(js)
    md = to_md(r)
    if a.md_out: Path(a.md_out).write_text(md)
    print(md if not a.json_out else f"score={s} band={band} -> {a.json_out}")


if __name__ == "__main__":
    main()
