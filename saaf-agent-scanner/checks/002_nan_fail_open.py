"""SAAF-002: numbers parsed from documents/uploads with float()/Decimal() (or default json.loads) are never checked with
isfinite/isnan, while the same codebase raises discrepancies with `abs(a - b) > tolerance` style comparisons. 'nan'
parses successfully and every comparison with NaN is False, so the discrepancy is never raised.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, functions, snippet

CHECK = {
    "id": "SAAF-002",
    "slug": "nan-accepted-fail-open",
    "category": "integrity-of-audit-conclusion",
    "severity": "Medium",
    "title": "NaN accepted as a number: values of 'nan' make every tolerance comparison false and the result is a silent pass",
    "intended": "Quantities, prices and amounts read from invoices, uploads or JSON are valid finite numbers; any value that "
                "differs from the reference beyond the tolerance is reported as a discrepancy.",
    "actual": "Values are converted with float()/Decimal() (or json.loads, which accepts NaN/Infinity) without a "
              "math.isfinite()/isnan() rejection, and the comparison logic raises discrepancies with checks such as "
              "abs(a - b) > tolerance. float('nan') (also 'NaN', 'inf') parses without error and every comparison with NaN "
              "is False.",
    "impact": "A document value of 'nan' (or an extreme/infinite value) passes every comparison, so a mismatching or "
              "fabricated line is reported as MATCH/OK and the audit conclusion is wrong without any error or warning. "
              "Whoever controls the input document can use this to bypass the control.",
    "recommendation": "Reject non-finite values at the parsing boundary (`if not math.isfinite(x): raise ParseError`; for "
                      "Decimal use `.is_finite()`), pass `parse_constant` to json.loads to refuse NaN/Infinity, and write "
                      "comparisons fail-closed, e.g. `if not (abs(a - b) <= tol): flag()` so that NaN is flagged.",
    "refs": "CWE-20, CWE-754, CWE-1389, OWASP LLM09",
}

# Tolerance-style comparison that raises a discrepancy when the difference is LARGE (NaN -> False -> silent pass).
TOL = r"[\w.\[\]\"']*(?:tol|toler|epsilon|eps|thresh|margin|allowed|limit)\w*"
CMP_ABS = re.compile(r"\babs\(\s*[^()]*?-[^()]*\)\s*>=?\s*(?:" + TOL + r"|\d*\.\d+(?:e-?\d+)?)", re.I)
CMP_DIFF = re.compile(r"\b\w*(?:diff|delta|disc|variance|deviation|mismatch|gap)\w*\s*>=?\s*" + TOL, re.I)
CMP_ABS_VAR = re.compile(r"\babs\(\s*\w*(?:diff|delta|disc|variance|deviation|mismatch|gap)\w*\s*\)\s*>=?\s*" + TOL, re.I)
FAILCLOSED = re.compile(r"not\s*\(\s*abs\(|\bnot\s+math\.isclose|\bnot\s+\(?\s*abs\(", re.I)

GUARD = re.compile(r"isfinite|isnan|is_nan|is_finite|\.isnan\(|np\.isfinite|pd\.isna|pd\.isnull|math\.isinf|isinf\(|"
                   r"allow_nan\s*=\s*False|parse_constant|\bx\s*!=\s*x\b|(\w+)\s*!=\s*\1\b", re.I)

# float()/Decimal() on a non-literal, non-trivial argument
CONV = re.compile(r"(?<![\w.])(?:float|Decimal|decimal\.Decimal)\(\s*(?!\s*[\"'](?:inf|-inf|nan)[\"'])(?![\d.\"'-]+\s*\))"
                  r"(?!\s*(?:len|os\.|sys\.|time\.|round|int|sum|\)))([A-Za-z_][\w.\[\]\"'()]*)")
JSON_LOAD = re.compile(r"\bjson\.loads?\(|\.json\(\)|\borjson\.loads|\bsimplejson\.loads?")
DOC_CTX = re.compile(r"pars|ingest|extract|upload|import|read|load|csv|excel|xlsx|invoice|coerce|normali[sz]|"
                     r"to_?float|to_?num|to_?dec|number|amount|qty|quantity|price|total", re.I)
SKIP_ARG = re.compile(r"^(?:self\.)?(?:tol|toler|epsilon|eps|thresh|timeout|delay|port|version|seed|temperature|"
                      r"max_|min_|rate|ratio|score)", re.I)


def _is_conv_context(path: str, head: str, line: str) -> bool:
    return bool(DOC_CTX.search(path) or DOC_CTX.search(head) or DOC_CTX.search(line))


def run(repo):
    cmp_hits = []       # (rel, idx, line)
    conv_hits = []      # (rel, idx, line, how)
    guarded_files = set()
    for rel in repo.files({".py"}):
        src = repo.read(rel)
        if not ("float(" in src or "Decimal(" in src or "abs(" in src or "json" in src):
            continue
        lines = repo.lines(rel)
        file_guard = bool(GUARD.search(src))
        file_cmp = []
        for i, l in enumerate(lines):
            s = l.split("#", 1)[0]
            if FAILCLOSED.search(s):
                continue
            if CMP_ABS.search(s) or CMP_DIFF.search(s) or CMP_ABS_VAR.search(s):
                file_cmp.append((rel, i, l))
        if file_guard:
            guarded_files.add(rel)
            # a guard anywhere in the file: no finding from this file (parse+compare either guarded or by design)
            continue
        cmp_hits += file_cmp
        for a, b, head in functions(lines):
            body = "\n".join(lines[a:b])
            if GUARD.search(body):
                continue
            for i in range(a, b):
                s = lines[i].split("#", 1)[0]
                m = CONV.search(s)
                if m and not SKIP_ARG.match(m.group(1)) and _is_conv_context(rel, head, s):
                    if re.search(r"\bint\(|\bround\(", s) and "float(" not in s and "Decimal(" not in s:
                        continue
                    conv_hits.append((rel, i, lines[i], "float/Decimal"))
                    break
        if file_cmp and JSON_LOAD.search(src):
            ln = next(i for i, l in enumerate(lines) if JSON_LOAD.search(l))
            conv_hits.append((rel, ln, lines[ln], "json (accepts NaN)"))
    # Pair a parse site with a comparison site only when they live in the same directory (same module/package
    # layer, as in parsers.py + matcher.py); a repo-wide pairing produced unrelated matches.
    d = lambda rel: rel.rsplit("/", 1)[0] if "/" in rel else ""
    conv_dirs = {d(c[0]) for c in conv_hits}
    cmp_hits = [c for c in cmp_hits if d(c[0]) in conv_dirs]
    cmp_dirs = {d(c[0]) for c in cmp_hits}
    conv_hits = [c for c in conv_hits if d(c[0]) in cmp_dirs]
    if not cmp_hits or not conv_hits:
        return []
    hits = []
    for rel, i, l in cmp_hits[:20]:
        hits.append(Hit(rel, i + 1, snippet(l), "tolerance comparison that is False for NaN (discrepancy silently not raised)"))
    for rel, i, l, how in conv_hits[:20]:
        hits.append(Hit(rel, i + 1, snippet(l), f"{how} parse without isfinite/isnan rejection"))
    return hits
