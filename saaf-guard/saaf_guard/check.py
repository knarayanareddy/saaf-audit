"""saaf-guard check — statische CI-check voor SAAF-agentrepos (alleen standaardbibliotheek).

Gebruik:
  python -m saaf_guard.check <repo-pad> [--history] [--json] [--fail-on high|medium|low|never]

Uitzonderingen: bestand .saaf-guard-ignore in de repo-root, één per regel:
  SG03 src/report.py   # reden (verplicht)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass

LANG = "nl"


def T(nl: str, en: str) -> str:
    """Kies de tekst in de actieve taal (nl/en)."""
    return en if LANG == "en" else nl


SEV = {"high": 3, "medium": 2, "low": 1}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", ".next", "dist", "build",
             "site-packages", ".pytest_cache", ".mypy_cache"}
TEST_HINT = re.compile(r"(^|[\\/])(tests?|fixtures?|__fixtures__|examples?|samples?)([\\/]|$)|(^|[\\/])test_[^\\/]*$|_test\.py$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$", re.I)

RULES = {
    "SG01": ("high", "Echte API-sleutel in werkboom of git-geschiedenis",
             "Sleutel intrekken, geschiedenis opschonen (git filter-repo), sleutels alleen via env/secret store."),
    "SG02": ("high", "Onvertrouwde tekst gaat de prompt in zonder fence()",
             "Wikkel document/upload/repo-tekst in saaf_guard.fence() en zet FENCE_RULE in de systeemprompt."),
    "SG03": ("high", "Fail-open eindoordeel: functie valt terug op een positieve uitkomst",
             "Gebruik saaf_guard.rollup(): leeg of onbekend => 'Inconclusive', nooit groen/match/go."),
    "SG04": ("medium", "Tolerantievergelijking zonder NaN/inf-controle",
             "Gebruik saaf_guard.within_tolerance() of math.isfinite() vóór abs(a-b) > tol."),
    "SG05": ("high", "Server open voor netwerk of andere websites",
             "Bind op 127.0.0.1, geen CORS '*', debug uit; endpoints die agents draaien of bestanden lezen achter een token."),
    "SG06": ("high", "Onveilige uitvoering (shell=True, eval/exec, pickle, yaml.load)",
             "Argumentlijst zonder shell, geen eval/exec op invoer, yaml.safe_load, geen pickle op externe data."),
    "SG07": ("medium", "Audit-trail/hashketen zonder geheime sleutel",
             "Gebruik saaf_guard.AuditTrail (HMAC, sleutel uit env, append-only, verify())."),
    "SG08": ("low", "CSV/Excel-export zonder formule-neutralisatie",
             "Haal elke celwaarde door saaf_guard.safe_cell()."),
    "SG09": ("high", "Server-token gaat mee naar een URL die uit verzoekparameters is gebouwd",
             "Valideer parameters met een strikte allowlist/regex (geen '..', '?', '#', '/') vóór fetch met token."),
    "SG11": ("medium", "Onge-escapete HTML-opbouw met variabele data (XSS)",
             "Gebruik textContent of escape (html.escape / een esc()-functie) voor elke waarde die in HTML komt."),
    "SG12": ("medium", "GET-route die data wijzigt of wist (CSRF, zonder auth aan te roepen)",
             "Maak het een POST/DELETE achter authenticatie en een expliciete bevestiging."),
    "SG13": ("medium", "Upload of bestand volledig ingelezen zonder groottelimiet",
             "Begrens de grootte vóór het inlezen (Content-Length/MAX_UPLOAD_BYTES, read(n)) en weiger grotere bestanden."),
    "SG14": ("low", "XML van buiten geparsed met de standaardbibliotheek",
             "Gebruik defusedxml (billion laughs / XXE) voor elk XML-bestand dat niet zelf gemaakt is."),
    "SG15": ("medium", "Archief uitgepakt zonder pad- en groottecontrole",
             "tarfile: extractall(filter='data'); zip: controleer infolist() op totale grootte en paden vóór uitpakken."),
    "SG16": ("high", "Template opgebouwd uit variabele invoer (SSTI)",
             "Gebruik vaste templates met variabelen als context; nooit render_template_string/Template() op invoer."),
    "SG17": ("medium", "Tekst stil afgekapt vóór de prompt",
             "Knip op in delen of weiger te lange invoer (fence(max_chars)); meld afkappen altijd in de uitkomst."),
    "SG10": ("low", "Extern script zonder versiepin of integrity-hash",
             "Pin de versie en voeg integrity=\"sha384-...\" + crossorigin toe, of host het bestand zelf."),
}

KEY_RE = re.compile(r"(sk-ant-[A-Za-z0-9_-]{80,}|sk-proj-[A-Za-z0-9_-]{40,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}|AKIA[0-9A-Z]{16}|xox[bp]-[0-9]{8,}-[0-9A-Za-z-]{20,})")
PLACEHOLDER = re.compile(r"x{4,}|your|example|placeholder|dummy|fake|redacted|\.\.\.|<", re.I)

LLM_CALL = re.compile(r"\.messages\.(create|stream)\(|\.chat\.completions\.create\(|\.responses\.create\(|anthropic\.|ChatAnthropic|ChatOpenAI|invoke_model|\.invoke\(")
UNTRUSTED_SRC = re.compile(
    r"UploadFile|request\.files|st\.file_uploader|PdfReader|pdfplumber|fitz\.open|pypdf|docx\.Document|"
    r"read_text\(|\.read\(\)|extract_text\(|requests\.get\(|urlopen\(|httpx\.|feedparser|git\s+clone|"
    r"open\([^)]*['\"]r")
POSITIVE = {"green", "match", "matched", "go", "pass", "passed", "low", "compliant", "sufficient",
            "validated", "approved", "ok", "verified", "supported", "effective", "clean"}
SAFE_EXPORT = re.compile(r"safe_cell|sanitiz|neutrali[sz]|formula|_csv_safe|escape_cell|excel_safe", re.I)
GENERATOR = re.compile(r"(^|/)(gen_|generate_|seed|make_sample|create_sample)[^/]*\.py$|(^|/)generators?/", re.I)
SAFE_EXPR = re.compile(r"esc|sanitiz|DOMPurify|encode|Number\(|parseInt|parseFloat|toFixed|toLocale|\.length|\bcount\b|\bidx\b|\bi\b|^\s*\d+\s*$|Math\.|\?\s*['\"][^'\"]*['\"]\s*:\s*['\"]", re.I)
SIZE_GUARD = re.compile(r"MAX_(UPLOAD|FILE|CONTENT)\w*|max_(upload|file|content)_?(size|bytes)|content_length|MAX_CONTENT_LENGTH|\.read\(\s*\d|maxUploadSize|server\.maxUploadSize|size\s*>\s*\d", re.I)
ABS_CMP_GUARD = re.compile(r"isfinite|isnan|math\.isinf|within_tolerance|require_finite|np\.isfinite|pd\.isna|notna")


@dataclass
class Hit:
    rule: str
    severity: str
    path: str
    line: int
    detail: str


def _rel(root, p):
    return os.path.relpath(p, root).replace("\\", "/")


def _walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            yield os.path.join(d, f)


def _read(p, limit=2_000_000):
    try:
        if os.path.getsize(p) > limit:
            return None
        with open(p, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return None


def _line(text, idx):
    return text.count("\n", 0, idx) + 1


# ------------------------------------------------------------------ Python (AST)

class _PyVisitor(ast.NodeVisitor):
    def __init__(self, src, add, path=""):
        self.src, self.add, self.path = src, add, path.replace("\\", "/")
        self.has_fence = "fence(" in src

    # SG03: laatste statement is 'return <positieve string>' na voorwaardelijke checks
    def visit_FunctionDef(self, node):
        body = node.body
        if body and isinstance(body[-1], ast.Return) and isinstance(getattr(body[-1], "value", None), ast.Constant):
            val = body[-1].value.value
            if isinstance(val, str) and val.strip().lower() in POSITIVE and any(isinstance(s, (ast.If, ast.For)) for s in body[:-1]):
                self.add("SG03", body[-1].lineno, T(f"{node.name}() eindigt met return '{val}' als terugval", f"{node.name}() falls back to return '{val}'"))
        # SG04: abs(a-b) > tol in functie zonder finite-check
        seg = ast.get_source_segment(self.src, node) or ""
        if not ABS_CMP_GUARD.search(seg):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and isinstance(sub.left, ast.Call) and getattr(sub.left.func, "id", "") == "abs" \
                        and any(isinstance(o, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) for o in sub.ops):
                    self.add("SG04", sub.lineno, T(f"abs(...) vergelijking in {node.name}() zonder isfinite/NaN-check", f"abs(...) comparison in {node.name}() without isfinite/NaN check"))
                    break
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        # SG06
        if name in ("run", "Popen", "call", "check_output", "check_call") and isinstance(kw.get("shell"), ast.Constant) and kw["shell"].value is True:
            if node.args and not isinstance(node.args[0], ast.Constant):
                self.add("SG06", node.lineno, T(f"subprocess.{name}(shell=True) met samengestelde opdracht", f"subprocess.{name}(shell=True) with a composed command"))
        if name in ("eval", "exec") and isinstance(f, ast.Name) and node.args and not isinstance(node.args[0], ast.Constant):
            self.add("SG06", node.lineno, T(f"{name}() op niet-constante invoer", f"{name}() on non-constant input"))
        if name in ("load", "loads") and isinstance(f, ast.Attribute) and getattr(f.value, "id", "") in ("pickle", "dill", "joblib"):
            self.add("SG06", node.lineno, T(f"{f.value.id}.{name}() op mogelijk externe data", f"{f.value.id}.{name}() on possibly external data"))
        if name == "load" and isinstance(f, ast.Attribute) and getattr(f.value, "id", "") == "yaml":
            loader = kw.get("Loader")
            if loader is None or "Safe" not in ast.unparse(loader):
                self.add("SG06", node.lineno, T("yaml.load zonder SafeLoader", "yaml.load without SafeLoader"))
        # SG16: template die uit tekst wordt samengesteld (SSTI): render_template_string / jinja Template / env.from_string
        base = ast.unparse(f.value) if isinstance(f, ast.Attribute) else ""
        is_tpl = name == "render_template_string" or (
            name == "Template" and re.search(r"jinja2|mako", self.src)) or (
            name == "from_string" and re.search(r"env|jinja", base, re.I))
        if is_tpl and node.args and isinstance(node.args[0], (ast.BinOp, ast.JoinedStr)) or (
                is_tpl and node.args and isinstance(node.args[0], ast.Call)
                and getattr(node.args[0].func, "attr", "") in ("format", "replace", "join")):
            self.add("SG16", node.lineno, T(f"{name}() met samengestelde template-tekst",
                                            f"{name}() with a template built from text"))
        # SG05: host 0.0.0.0, debug=True, CORS *
        if name == "run" and isinstance(kw.get("host"), ast.Constant) and kw["host"].value in ("0.0.0.0", "::"):
            self.add("SG05", node.lineno, T(f"server bindt op {kw['host'].value}", f"server binds to {kw['host'].value}"))
        if name == "run" and isinstance(kw.get("debug"), ast.Constant) and kw["debug"].value is True:
            self.add("SG05", node.lineno, "debug=True")
        if name == "add_middleware" and "allow_origins" in kw and "'*'" in ast.unparse(kw["allow_origins"]):
            self.add("SG05", node.lineno, "CORS allow_origins=['*']")
        if name == "CORS" and ("origins" not in kw or "'*'" in ast.unparse(kw.get("origins", ast.Constant("*")))):
            self.add("SG05", node.lineno, T("flask_cors CORS() zonder origin-beperking", "flask_cors CORS() without origin restriction"))
        # SG08
        if name in ("writerow", "writerows", "append") and not SAFE_EXPORT.search(self.src) and not GENERATOR.search(self.path):
            base = ast.unparse(f.value) if isinstance(f, ast.Attribute) else ""
            if name != "append" or re.search(r"\b(ws|sheet|worksheet)\b", base):
                self.add("SG08", node.lineno, T(f"{base}.{name}() zonder safe_cell()", f"{base}.{name}() without safe_cell()"))
        if name in ("to_csv", "to_excel") and not SAFE_EXPORT.search(self.src) and not GENERATOR.search(self.path):
            self.add("SG08", node.lineno, T(f"DataFrame.{name}() zonder formule-neutralisatie", f"DataFrame.{name}() without formula neutralisation"))
        self.generic_visit(node)


def scan_python(path, src, add):
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return
    _PyVisitor(src, add, path).visit(tree)
    # SG11: HTML via f-string/format met data, zonder html.escape in het bestand
    if not re.search(r"html\.escape|markupsafe|escape\(|bleach", src):
        m = re.search(r"f[\"']{1,3}[^\n]*<(td|li|p|div|span|h\d|a )[^\n]*\{[a-zA-Z_]", src)
        if m:
            add("SG11", _line(src, m.start()), T("HTML-string met {variabele} zonder html.escape", "HTML string with {variable} without html.escape"))
    # SG02: LLM-aanroep + onvertrouwde bron in hetzelfde bestand, zonder fence()
    m = LLM_CALL.search(src)
    if m and UNTRUSTED_SRC.search(src) and "fence(" not in src and "<untrusted" not in src:
        add("SG02", _line(src, m.start()), T("LLM-aanroep in bestand dat documenten/uploads/web leest, geen fence()", "LLM call in a file that reads documents/uploads/web, no fence()"))
    # SG13: upload/bestand volledig inlezen zonder groottelimiet
    if re.search(r"UploadFile|request\.files|st\.file_uploader|FileStorage", src) and not SIZE_GUARD.search(src):
        m = re.search(r"\.(read|getvalue)\(\s*\)", src)
        if m:
            add("SG13", _line(src, m.start()), T("upload volledig ingelezen, geen groottelimiet in dit bestand",
                                                  "upload read fully, no size limit in this file"))
    # SG14: XML met de standaardbibliotheek
    if not re.search(r"defusedxml", src):
        m = re.search(r"(xml\.etree\.ElementTree\.(parse|fromstring)|ET\.(parse|fromstring)|minidom\.parse(String)?|xml\.sax\.parse|etree\.(parse|fromstring)\()", src)
        if m:
            add("SG14", _line(src, m.start()), T(f"{m.group(0)} zonder defusedxml", f"{m.group(0)} without defusedxml"))
    # SG15: archief uitpakken
    for m in re.finditer(r"\.extractall\(([^)]*)\)", src):
        if "filter=" in m.group(1):
            continue
        ctx = src[max(0, m.start() - 1500): m.start()]
        if re.search(r"file_size|infolist\(\)|getmembers\(\)|is_relative_to|commonpath|realpath", ctx):
            continue
        add("SG15", _line(src, m.start()), T("extractall() zonder pad/groottecontrole", "extractall() without path/size check"))
        break
    # SG17: stille afkapping van tekst vóór een LLM-aanroep (grote vaste of max_-limiet; niet in log/fout/commentaar;
    #       een melding van het afkappen binnen 3 regels telt als 'gemeld')
    if LLM_CALL.search(src):
        code = re.sub(r"#[^\n]*", "", src)
        lines = code.split("\n")
        disclosed = re.compile(r"truncated\w*\s*[=:]|[\"'][^\"'\n]*(truncated|afgekapt)[^\"'\n]*[\"']", re.I)
        for m in re.finditer(r"\b(\w*(?i:text|content|doc|document|body|policy|evidence|pdf|chunk)\w*)\s*\[\s*:\s*(\d{4,}|[A-Z][A-Z_]{2,}|(?i:max|limit)_?\w*)\s*\]", code):
            ln = _line(code, m.start())
            line = lines[ln - 1]
            if re.search(r"\b(raise|print|log\w*|logger|warn\w*|error|repr)\b|!r|'raw'|\"raw\"", line, re.I):
                continue
            if disclosed.search("\n".join(lines[max(0, ln - 4): ln + 3])):
                continue
            add("SG17", ln, T(f"{m.group(0)} vóór LLM-aanroep, afkappen niet gemeld",
                              f"{m.group(0)} before LLM call, truncation not disclosed"))
            break
    # SG07: hashketen zonder hmac
    if re.search(r"prev(ious)?_?hash|hash_?chain|chain_hash", src) and "hashlib.sha" in src and "hmac" not in src:
        mm = re.search(r"hashlib\.sha\w*", src)
        add("SG07", _line(src, mm.start()), T("hashketen met hashlib zonder HMAC-sleutel", "hash chain with hashlib, no HMAC key"))


# ------------------------------------------------------------------ overige bestanden (regex)

def scan_text(path, src, add):
    low = path.lower()
    if low.endswith((".ts", ".tsx", ".js", ".mjs", ".cjs")):
        for m in re.finditer(r"Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*|origin\s*:\s*['\"]\*['\"]|\bcors\(\s*\)", src):
            add("SG05", _line(src, m.start()), T("CORS '*' in JS/TS-server", "CORS '*' in JS/TS server"))
        for m in re.finditer(r"listen\([^)]*['\"]0\.0\.0\.0['\"]", src):
            add("SG05", _line(src, m.start()), T("server luistert op 0.0.0.0", "server listens on 0.0.0.0"))
        # SG09: token in fetch naar URL met ${...} uit request-parameters
        if re.search(r"process\.env\.\w*(PAT|TOKEN|KEY|SECRET)\w*", src) and re.search(r"searchParams\.get\(|req\.query|params\.\w+|await request\.json\(\)", src):
            for m in re.finditer(r"fetch\(\s*`[^`]*\$\{", src):
                seg = src[max(0, m.start() - 1500): m.start()]
                if not re.search(r"\.test\(|match\(|/\^\[|allowlist|ALLOWED|isValid|encodeURIComponent", seg):
                    add("SG09", _line(src, m.start()), T("fetch met server-token naar URL uit verzoekparameters, geen validatie", "fetch with server token to a URL built from request parameters, no validation"))
    if low.endswith((".html", ".htm", ".js", ".mjs", ".jsx")):
        # SG11: per ${...} in een innerHTML-template kijken of de waarde zelf ge-escaped wordt
        for m in re.finditer(r"(\.(?:innerHTML|outerHTML)\s*\+?=\s*|insertAdjacentHTML\([^,]+,\s*)`([^`]*)`", src):
            raw = [e for e in re.findall(r"\$\{([^}]*)\}", m.group(2)) if not SAFE_EXPR.search(e)]
            if raw:
                add("SG11", _line(src, m.start()), T("innerHTML met onge-escapete waarde ${%s}", "innerHTML with unescaped value ${%s}") % raw[0].strip()[:40])
                break  # een melding per bestand: zelfde oorzaak
    if low.endswith((".ts", ".js")):
        for m in re.finditer(r"export\s+(?:async\s+)?function\s+GET\b", src):
            body = src[m.end(): m.end() + 3000].split("export ", 1)[0]
            if re.search(r"\b(seed\w*|reset\w*|wipe\w*|clear\w*|purge\w*|delete\w*|remove\w*|drop\w*|truncate\w*|upsert|insert\w*)\s*\(|DELETE FROM|TRUNCATE|DROP TABLE", body, re.I):
                add("SG12", _line(src, m.start()), T("GET-handler voert schrijf/verwijderacties uit", "GET handler performs write/delete actions"))
    if low.endswith((".html", ".htm", ".js", ".ts", ".tsx", ".jsx")):
        for m in re.finditer(r"<script[^>]+src=['\"]https?://(cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|esm\.sh)[^'\"]*['\"][^>]*>", src):
            if "integrity=" not in m.group(0):
                add("SG10", _line(src, m.start()), T("CDN-script zonder integrity", "CDN script without integrity"))
        for m in re.finditer(r"import\(\s*['\"]https?://(cdn\.jsdelivr\.net|unpkg\.com|esm\.sh)/([^'\"]+)['\"]", src):
            if not re.search(r"@\d", m.group(2)):
                add("SG10", _line(src, m.start()), T("dynamische import van CDN zonder versiepin", "dynamic CDN import without version pin"))
    if low.endswith((".yml", ".yaml", ".toml", ".sh", ".ps1", ".bat", ".cmd", "dockerfile", ".json")):
        for m in re.finditer(r"(--server\.address[ =]0\.0\.0\.0|--host[ =]0\.0\.0\.0|address\s*=\s*['\"]0\.0\.0\.0)", src):
            add("SG05", _line(src, m.start()), T("start-configuratie bindt op 0.0.0.0", "start configuration binds to 0.0.0.0"))


def scan_secrets_tree(root, path, src, add):
    for m in KEY_RE.finditer(src):
        if not PLACEHOLDER.search(m.group(0)):
            add("SG01", _line(src, m.start()), T(f"{m.group(0)[:7]}… (waarde niet getoond)", f"{m.group(0)[:7]}… (value not shown)"))


def scan_history(root):
    hits = []
    try:
        out = subprocess.run(["git", "-C", root, "log", "--all", "-p", "--no-color", "--format=@@C %h"],
                             capture_output=True, text=True, errors="ignore", timeout=600).stdout
    except (OSError, subprocess.TimeoutExpired):
        return hits
    commit = f = None
    seen = set()
    for l in out.splitlines():
        if l.startswith("@@C "):
            commit = l[4:].strip()
        elif l.startswith("+++ "):
            f = l[6:].strip()
        elif l.startswith("+") and not l.startswith("+++"):
            for m in KEY_RE.finditer(l):
                if not PLACEHOLDER.search(m.group(0)) and (f, m.group(0)[:12]) not in seen:
                    seen.add((f, m.group(0)[:12]))
                    hits.append(Hit("SG01", "high", f"{f} @ {commit}", 0, T(f"{m.group(0)[:7]}… in git-geschiedenis (waarde niet getoond)", f"{m.group(0)[:7]}… in git history (value not shown)")))
    return hits


# ------------------------------------------------------------------ hoofdprogramma

def load_ignores(root):
    ign = []
    p = os.path.join(root, ".saaf-guard-ignore")
    if os.path.exists(p):
        for raw in open(p, encoding="utf-8"):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "#" not in line:
                print(T(f"waarschuwing: uitzondering zonder reden genegeerd: {line}", f"warning: exception without reason ignored: {line}"), file=sys.stderr)
                continue
            rule, _, rest = line.partition(" ")
            ign.append((rule.strip(), rest.split("#")[0].strip()))
    return ign


def scan(root, history=False, include_tests=False):
    hits = []
    for p in _walk(root):
        rel = _rel(root, p)
        if not include_tests and TEST_HINT.search(rel):
            continue
        if not re.search(r"\.(py|ts|tsx|js|mjs|cjs|jsx|html?|ya?ml|toml|sh|ps1|bat|cmd|json|env|cfg|ini|md|txt)$|dockerfile$|\.env", rel, re.I):
            continue
        src = _read(p)
        if src is None:
            continue

        def add(rule, line, detail, _rel=rel):
            hits.append(Hit(rule, RULES[rule][0], _rel, line, detail))

        scan_secrets_tree(root, p, src, add)
        if rel.endswith(".py"):
            scan_python(p, src, add)
        else:
            scan_text(p, src, add)
    if history:
        hits.extend(scan_history(root))
    ign = load_ignores(root)
    return [h for h in hits if not any(r in (h.rule, "*") and (not pth or h.path.startswith(pth)) for r, pth in ign)]


RULES_EN = {
    "SG01": ("Real API key in working tree or git history",
             "Revoke the key, purge history (git filter-repo), keep keys in env/secret store only."),
    "SG02": ("Untrusted text enters the prompt without fence()",
             "Wrap document/upload/repo text in saaf_guard.fence() and put FENCE_RULE in the system prompt."),
    "SG03": ("Fail-open verdict: function falls back to a positive outcome",
             "Use saaf_guard.rollup(): empty or unknown => 'Inconclusive', never green/match/go."),
    "SG04": ("Tolerance comparison without NaN/inf check",
             "Use saaf_guard.within_tolerance() or math.isfinite() before abs(a-b) > tol."),
    "SG05": ("Server open to the network or other websites",
             "Bind to 127.0.0.1, no CORS '*', debug off; put endpoints that run agents or read files behind a token."),
    "SG06": ("Unsafe execution (shell=True, eval/exec, pickle, yaml.load)",
             "Argument list without shell, no eval/exec on input, yaml.safe_load, no pickle on external data."),
    "SG07": ("Audit trail / hash chain without a secret key",
             "Use saaf_guard.AuditTrail (HMAC, key from env, append-only, verify())."),
    "SG08": ("CSV/Excel export without formula neutralisation",
             "Pass every cell value through saaf_guard.safe_cell()."),
    "SG09": ("Server token sent to a URL built from request parameters",
             "Validate parameters with a strict allowlist/regex (no '..', '?', '#', '/') before fetching with a token."),
    "SG10": ("External script without version pin or integrity hash",
             "Pin the version and add integrity=\"sha384-...\" + crossorigin, or self-host the file."),
    "SG11": ("Unescaped HTML built from variable data (XSS)",
             "Use textContent or escape (html.escape / an esc() function) for every value placed in HTML."),
    "SG12": ("GET route that changes or deletes data (CSRF, callable without auth)",
             "Make it a POST/DELETE behind authentication and an explicit confirmation."),
    "SG13": ("Upload or file read fully into memory without a size limit",
             "Limit size before reading (Content-Length/MAX_UPLOAD_BYTES, read(n)) and reject larger files."),
    "SG14": ("External XML parsed with the standard library",
             "Use defusedxml (billion laughs / XXE) for any XML you did not create yourself."),
    "SG15": ("Archive extracted without path and size checks",
             "tarfile: extractall(filter='data'); zip: check infolist() for total size and paths before extracting."),
    "SG16": ("Template built from variable input (SSTI)",
             "Use fixed templates with variables as context; never render_template_string/Template() on input."),
    "SG17": ("Text silently truncated before the prompt",
             "Chunk or reject over-long input (fence(max_chars)); always disclose truncation in the result."),
}


def rule_text(rule: str):
    """(severity, titel, fix) in de actieve taal."""
    sev, title, fix = RULES[rule]
    if LANG == "en":
        title, fix = RULES_EN[rule]
    return sev, title, fix


def set_lang(lang: str) -> None:
    global LANG
    LANG = "en" if str(lang).lower().startswith("en") else "nl"


def main(argv=None):
    ap = argparse.ArgumentParser(description="SAAF Guard — CI check against known agent flaws / CI-check tegen bekende agent-fouten")
    ap.add_argument("repo")
    ap.add_argument("--history", action="store_true", help="scan full git history for keys / ook de git-geschiedenis scannen")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--include-tests", action="store_true")
    ap.add_argument("--fail-on", default="high", choices=["high", "medium", "low", "never"])
    ap.add_argument("--lang", default=os.environ.get("SAAF_GUARD_LANG", "nl"), choices=["nl", "en"])
    a = ap.parse_args(argv)
    set_lang(a.lang)
    hits = scan(a.repo, a.history, a.include_tests)
    hits.sort(key=lambda h: (-SEV[h.severity], h.rule, h.path, h.line))
    if a.json:
        print(json.dumps([asdict(h) for h in hits], ensure_ascii=False, indent=1))
    else:
        for h in hits:
            loc = f"{h.path}:{h.line}" if h.line else h.path
            print(f"[{h.severity.upper():6}] {h.rule} {loc}  {h.detail}")
            print(f"         fix: {rule_text(h.rule)[2]}")
        print(f"\nSAAF Guard: {len(hits)} {T('meldingen', 'findings')} "
              f"({sum(h.severity == 'high' for h in hits)} high, {sum(h.severity == 'medium' for h in hits)} medium, "
              f"{sum(h.severity == 'low' for h in hits)} low)")
    if a.fail_on == "never":
        return 0
    return 1 if any(SEV[h.severity] >= SEV[a.fail_on] for h in hits) else 0


if __name__ == "__main__":
    sys.exit(main())
