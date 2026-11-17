"""SAAF-003: fail-open control logic. A comparison/discrepancy check is only evaluated when every operand is present
("a is not None and b is not None and a != b"), with no branch that reports the missing operand, so absent data yields
the default pass verdict; or a verdict/status read from model/parsed output defaults to a passing value
(.get("verdict", "N-A")).
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, functions, snippet

CHECK = {
    "id": "SAAF-003",
    "slug": "missing-value-skips-check",
    "category": "integrity-of-audit-conclusion",
    "severity": "Low",
    "title": "Fail-open verdict logic: a missing value skips the check or defaults the verdict to a passing value",
    "intended": "A control whose input is missing, empty or unrecognised is reported as an exception (FAIL/WARN/'manual "
                "review required'); the audit conclusion is only 'pass' when the check was actually performed.",
    "actual": "Either the discrepancy test is guarded by 'x is not None and y is not None and ...' (or 'if x and y ...') "
              "with no else-branch or 'is None' handling, so a missing operand silently skips the comparison and the "
              "default verdict stays MATCH/PASS; or the verdict/status is read with a passing default such as "
              ".get('verdict', 'N-A'|'PASS'|'compliant') so an omitted or injected-away value is recorded as a pass.",
    "impact": "Stripped, mis-labelled or malformed input (an invoice line without quantity/price, a model reply without a "
              "'verdict' key, a column header in another language) is certified as passing, creating false assurance "
              "with no signal to the reviewer.",
    "recommendation": "Treat absence as a result: require the operands and raise/FAIL (or WARN with 'manual review "
                      "required') when they are None or empty; read verdicts without a pass default, validate them "
                      "against the allowed set (case-normalised) and fall back to WARN/UNVERIFIED; add a test with "
                      "missing, empty and unrecognised fields that expects a non-pass outcome.",
    "refs": "CWE-636, CWE-754, OWASP LLM09",
}

# --- variant A: guarded comparison -------------------------------------------------------------------------------
IF_RE = re.compile(r"^(\s*)(?:el)?if\s+\(?(.*?)\)?\s*:\s*(#.*)?$")
NOTNONE = re.compile(r"([A-Za-z_][\w.\[\]\"']*)\s+is\s+not\s+None")
SIMPLE = re.compile(r"^[A-Za-z_]\w*(?:\.\w+)?$")
CMP = re.compile(r"abs\(|[<>]=?|!=|==")
AUDIT_WORDS = re.compile(r"toleran|mismatch|discrepan|differs|varianc|\bFAIL\b|\bWARN|\bflag|finding|issue|deviat", re.I)
PASS_LIT = re.compile(r"[\"'](MATCH|PASS|PASSED|OK|COMPLIANT|SUFFICIENT|ADEQUATE|EFFECTIVE|APPROVE[D]?|CLEAN)[\"']|"
                      r"=\s*True\b|return\s+True\b", re.I)


def _guard_names(cond: str):
    """Operands guarded by 'is not None' (>=2) or by bare truthiness (>=2 simple names), plus a comparison clause."""
    parts = [p.strip().strip("()") for p in re.split(r"\s+and\s+", cond)]
    names = [m.group(1) for p in parts for m in [NOTNONE.fullmatch(p)] if m]
    if len(set(names)) >= 2 and any(CMP.search(p) and " is not None" not in p for p in parts):
        return list(dict.fromkeys(names))
    bare = [p for p in parts if SIMPLE.match(p) and p not in ("True", "False", "None")]
    rest = [p for p in parts if p not in bare]
    # bare-truthiness guards only count for numeric/tolerance comparisons (abs(a-b) > tol); 'if role_a and role_b and
    # role_a != role_b' on strings is usually a deliberate "blank = not provided" skip and is too ambiguous to flag
    if len(set(bare)) >= 2 and any(re.search(r"abs\(|toleran", p, re.I) and all(re.search(rf"\b{re.escape(n)}\b", p) for n in bare[:2])
                                   for p in rest):
        return list(dict.fromkeys(bare))
    return []


def _has_else(lines, i, indent):
    """True when the if-block starting at line i is followed by an else/elif at the same indentation."""
    for j in range(i + 1, min(len(lines), i + 40)):
        l = lines[j]
        if not l.strip() or l.lstrip().startswith("#"):
            continue
        ind = len(l) - len(l.lstrip())
        if ind > indent:
            continue
        return ind == indent and re.match(r"\s*(else\s*:|elif\b)", l) is not None
    return False


def _variant_a(rel, lines, src):
    if not PASS_LIT.search(src):
        return []
    hits = []
    for a, b, head in functions(lines):
        body = lines[a:b]
        text = "\n".join(body)
        if not AUDIT_WORDS.search(text):
            continue
        for k, line in enumerate(body):
            m = IF_RE.match(line)
            if not m:
                continue
            names = _guard_names(m.group(2))
            if not names:
                continue
            others = "\n".join(l for n, l in enumerate(body) if n != k)
            handled = any(re.search(rf"(?<![\w.]){re.escape(n)}\s+is\s+None|\bnot\s+{re.escape(n)}\b|"
                                    rf"\b{re.escape(n)}\s*(==|!=)\s*None|\bisnan\(\s*{re.escape(n)}|"
                                    rf"if\s+{re.escape(n)}\s*(and|:)|if\s+not\s+\w*\s*{re.escape(n)}", others)
                          for n in names)
            if handled or _has_else(lines, a + k, len(m.group(1))):
                continue
            hits.append(Hit(rel, a + k + 1, snippet(line),
                            f"{head[:50]}: comparison only runs when {', '.join(names[:3])} are present; no branch "
                            f"reports a missing value (default verdict stays a pass)"))
            break  # one location per function
    return hits


# --- variant B: verdict parsing with a passing default -----------------------------------------------------------
PASSV = (r"PASS(?:ED)?|OK|N[/_ -]?A|NOT[ _-]APPLICABLE|COMPLIANT|SUFFICIENT|ADEQUATE|EFFECTIVE|MATCH(?:ED)?|"
         r"APPROVED?|VALID|NO[ _-]?ISSUES?|CLEAN|SATISFACTORY")
STRONG_KEYS = r"verdict|conclusion|outcome|compliance|sufficiency|assessment|determination|conformity|opinion"
WEAK_KEYS = r"status|result|decision|rating"
BOOL_KEYS = r"passed|compliant|sufficient|adequate|effective|approved|verified|valid|ok|match(?:es|ed)?"
GET_STR = re.compile(rf"\.get\(\s*[\"'](?P<k>{STRONG_KEYS}|{WEAK_KEYS})[\"']\s*,\s*[\"'](?P<v>{PASSV})[\"']\s*\)", re.I)
GET_BOOL = re.compile(rf"\.get\(\s*[\"'](?P<k>{BOOL_KEYS})[\"']\s*,\s*True\s*\)", re.I)
OR_STR = re.compile(rf"(?:\.get\(\s*[\"'](?P<k>{STRONG_KEYS}|{WEAK_KEYS})[\"']\s*\)|\[\s*[\"'](?P<k2>{STRONG_KEYS})[\"']\s*\]|"
                    rf"\b(?P<k3>{STRONG_KEYS})\b)\s*(?:\bor\b|\?\?|\|\|)\s*[\"'](?P<v>{PASSV})[\"']", re.I)
WEAK = re.compile(WEAK_KEYS, re.I)
AUDIT_FILE = re.compile(r"verdict|audit|control|finding|complian|assurance|evidence|sufficien", re.I)
SAFE_CTX = re.compile(r"\b(?:print|log\w*|render|display|label|html|format)\b|f[\"']", re.I)


def _variant_b(rel, lines, src):
    hits = []
    audit_file = bool(AUDIT_FILE.search(src))
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith(("#", "//", "*")) or "[" in s[:1] or len(s) > 300:
            continue
        m = GET_STR.search(line) or GET_BOOL.search(line) or OR_STR.search(line)
        if not m:
            continue
        key = (m.groupdict().get("k") or m.groupdict().get("k2") or m.groupdict().get("k3") or "").lower()
        v = (m.groupdict().get("v") or "").upper()
        if WEAK.fullmatch(key) and (not audit_file or re.fullmatch(r"N[/_ -]?A|NOT[ _-]APPLICABLE", v)):
            continue  # generic keys: N/A is a display placeholder, not a pass verdict
        if SAFE_CTX.search(line[:m.start()]) and not re.match(r"\s*\w+\s*=|.*\breturn\b", line):
            continue  # inside an f-string / print / render call: display default only
        if re.search(r"requests?\.|response\.(?:status|get)|status_code|http", line, re.I):
            continue
        hits.append(Hit(rel, i + 1, snippet(line),
                        f"'{key}' read with passing default '{m.groupdict().get('v') or 'True'}': a missing value is "
                        f"recorded as a pass"))
    return hits


def run(repo):
    hits = []
    for rel in repo.files({".py"}):
        src = repo.read(rel)
        if "None" not in src and "get(" not in src:
            continue
        lines = repo.lines(rel)
        hits += _variant_a(rel, lines, src)
        hits += _variant_b(rel, lines, src)
    for rel in repo.files({".ts", ".js", ".mjs", ".tsx", ".jsx"}):
        src = repo.read(rel)
        if "??" not in src and "||" not in src:
            continue
        hits += _variant_b(rel, repo.lines(rel), src)
    return hits
