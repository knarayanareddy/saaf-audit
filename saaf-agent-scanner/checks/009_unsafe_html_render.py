"""SAAF-009: model output or document/record content is rendered as raw HTML (innerHTML, dangerouslySetInnerHTML,
|safe, Markup, unsafe_allow_html, HTML f-strings) or as Markdown that allows remote images/links, without escaping.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, snippet, redact

CHECK = {
    "id": "SAAF-009",
    "slug": "unsafe-html-markdown-render",
    "category": "unsafe-output-rendering-xss",
    "severity": "Medium",
    "title": "Model output or document content is rendered as raw HTML or unrestricted Markdown without escaping",
    "intended": "Text produced by the model or taken from audited documents, uploads, tickets or records is shown as inert "
                "text: it is HTML-escaped (or set via textContent), or Markdown is rendered through a sanitiser that "
                "also blocks remote images and unsafe link schemes.",
    "actual": "The page or report builds HTML from model/document fields with innerHTML, outerHTML, "
              "insertAdjacentHTML, document.write, dangerouslySetInnerHTML, Jinja |safe/Markup()/autoescape=False, "
              "st.markdown(..., unsafe_allow_html=True) or f-strings, or renders Markdown with marked/markdown-it "
              "(without DOMPurify, or with DOMPurify default config that keeps remote <img>). The interpolated values "
              "are not passed through an escape function.",
    "impact": "A prompt injection or a crafted document/ticket/file name can return <img onerror=...> or <script> and run "
              "JavaScript in the auditor's browser (stored XSS: session tokens, API keys held in storage, actions as "
              "the auditor). Even sanitised Markdown with remote images lets injected text exfiltrate other "
              "submitted data through an image URL when the report is viewed, and can spoof report content.",
    "recommendation": "Escape every interpolated value (html.escape / escapeHtml) or assign textContent; build DOM nodes "
                      "instead of HTML strings; render Markdown only through DOMPurify with FORBID_TAGS ['img'] and "
                      "ALLOWED_URI_REGEXP restricted to https/mailto (or disable images in the renderer); never use "
                      "|safe/Markup/unsafe_allow_html on untrusted values; add a Content-Security-Policy with "
                      "img-src 'self' and no inline script.",
    "refs": "CWE-79, CWE-80, CWE-116, OWASP LLM05 (Improper Output Handling)",
}

EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".html", ".htm", ".vue", ".svelte", ".j2", ".jinja"}
WORDS = {"verdict", "rationale", "description", "desc", "text", "content", "summary", "answer", "response", "reply",
         "output", "msg", "title", "reason", "reasons", "reasoning", "note", "notes", "comment", "body",
         "markdown", "observation", "recommendation", "evidence", "link", "url", "href",
         "filename", "owner", "claimed", "rawmarkdown", "completion", "explanation", "analysis",
         "feedback", "snippet", "excerpt", "quote", "objective", "deadline", "citation", "justification",
         "remediation", "narrative", "conclusion", "assessment"}
GENERATED = {"badge", "pill", "html", "cls", "class", "icon", "chip", "markup", "svg", "tag"}
STATIC_ROOTS = {"t", "tr", "_l", "l", "i18n", "lang", "labels", "strings", "texts", "translations", "self", "cls"}
NUMERIC = re.compile(r"\.length\b|toFixed|Math\.|Number\(|parseInt|parseFloat|\bcount\b|\btotal\b|\bidx\b|\bindex\b|"
                     r"\bpct\b|percent|\bint\(|\bfloat\(|\blen\(|\bround\(|toLocale|\bsum\(|\.size\b|_count\b|_id\b|"
                     r"\.id\b|\bi\b|\bn\b|Date\(|isoformat|strftime|\.padStart")
ESCAPER = re.compile(r"(?:\b_?esc\w*|\w*[eE]scape\w*|\w*[sS]anitiz\w*|DOMPurify|\bbleach\b|\w*[eE]ncode\w*|\bquote\w*|"
                     r"\b_?h|\b_?e|\bhtml_escape|\bstrip_tags|\bsafe_\w+|\bjson\.dumps|\bJSON\.stringify)\s*\(|"
                     r"\.replace\(\s*/?[\"']?[<&\"]|textContent|\|\s*e\b|\|\s*escape\b")
HTMLISH_CALL = re.compile(r"^\s*(?:render|build|make|format|fmt|badge|pill|chip)\w*\(|(?:Html|HTML|Badge|Pill|Row|Card)\w*\(\s*"
                          r"[^)]*\)\s*$")
ERRVAR = re.compile(r"^(?:e|err|error|exc|ex)(?:\.(?:message|msg|stack|name))?$|^(?:e|err|error)\.\w+$")
TOK = re.compile(r"[A-Za-z_$][\w$]*")


def _strip_cond(e: str, py: bool) -> str:
    """Drop the condition of a ternary: only its branches are output."""
    if py:
        m = re.match(r"^(.*?)\s+if\s+.*?\s+else\s+(.*)$", e, re.S)
        return f"{m.group(1)} {m.group(2)}" if m else e
    segs, delims, depth, q, last = [], [], 0, "", 0
    for k, ch in enumerate(e):
        if q:
            if ch == q and e[k - 1] != "\\":
                q = ""
        elif ch in "\"'`":
            q = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and ch == "?" and e[k + 1:k + 2] not in (".", "?") and e[k - 1:k] not in ("?", " ") or \
                (depth == 0 and ch == "?" and e[k + 1:k + 2] == " " and e[k - 1:k] == " "):
            segs.append(e[last:k]); delims.append("?"); last = k + 1
        elif depth == 0 and ch == ":" and delims and delims.count("?") > delims.count(":"):
            segs.append(e[last:k]); delims.append(":"); last = k + 1
    if not delims:
        return e
    segs.append(e[last:])
    delims.append("")
    return " ".join(sg for sg, d in zip(segs, delims) if d != "?")


def _words(tok: str):
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", tok).lower().split("_")
    return [p for p in parts if p] + [tok.lower()]


def _dataish(expr: str) -> bool:
    """True if expr (a single interpolated expression, nested templates already removed) looks like it carries
    model output / document / record text and is not escaped or numeric."""
    e = _strip_cond(expr.strip(), False)
    if not e or e[0] in "\"'" and e[-1] == e[0] and e.count(e[0]) == 2 or "``" in e:
        return False
    if ESCAPER.search(e) or NUMERIC.search(e) or ERRVAR.match(e) or HTMLISH_CALL.search(e):
        return False
    if re.fullmatch(r"[\w$.]+\(\s*(?:[\"'][^\"']*[\"']\s*,?\s*)*\)", e) and not re.search(r"\.get\(|\bgetattr\(", e):
        return False                                                  # helper call with literal args only
    e2 = re.sub(r"\"[^\"]*\"|'[^']*'", "''", e)
    for tok in re.findall(r"[A-Za-z_$][\w$]*(?![\w$]|\s*\()", e2):
        ws = _words(tok)
        if any(w in WORDS for w in ws) and not any(w in GENERATED for w in ws):
            return True
    return False


CONST_ROOT = re.compile(r"^_?[A-Z][A-Z0-9_]{2,}$")


def _root(expr: str) -> str:
    m = TOK.search(expr)
    return m.group(0) if m else ""


def _local_safe(lines, i, expr, py, depth=0):
    bare = re.fullmatch(r"\s*[A-Za-z_$][\w$]*\s*", expr) is not None
    """True if the expression's root identifier is a constant, a translation table, a function parameter, a callback
    variable over a constant list, or was assigned from an escape call shortly before use."""
    root = _root(expr)
    if not root:
        return True
    if CONST_ROOT.match(root) or root.lower() in STATIC_ROOTS:
        return True
    r = re.escape(root)
    lo = max(0, i - 80)
    for k in range(i, lo - 1, -1):
        l = lines[k]
        if py:
            if re.match(r"\s*(?:async\s+)?def\s+\w+\s*\(", l):
                # parameter of the enclosing function (signature may span lines)
                sig = " ".join(lines[k:k + 8]).split("):")[0].split(") ->")[0]
                if bare and re.search(r"[(,\s*]" + r + r"\s*(?:[:=,)]|$)", sig):
                    return True
                break
            if re.match(r"\s*" + r + r"\s*=[^=]", l) and PY_ESC.search(l):
                return True
            if re.match(r"\s*for\s+[\w,\s()]*\b" + r + r"\b[\w,\s()]*\s+in\s+_?[A-Z][A-Z0-9_]{2,}\b", l):
                return True
        else:
            if re.search(r"\b(?:const|let|var)\s+" + r + r"\s*=[^=]", l) and ESCAPER.search(l):
                return True
            if re.search(r"\b" + r + r"\s*=\s*" + ESCAPER.pattern, l):
                return True
            mm = re.search(r"([A-Za-z_$][\w$.]*)\.(?:forEach|map|filter|flatMap|some|find)\(\s*\(?\s*" + r + r"\b", l)
            if mm and depth < 3 and (CONST_ROOT.match(_root(mm.group(1))) or _local_safe(lines, k, _root(mm.group(1)), py, depth + 1)):
                return True
            if bare and re.search(r"function\s*\w*\s*\([^)]*\b" + r + r"\b[^)]*\)|\(\s*[^()]*\b" + r + r"\b[^()]*\)\s*=>|\b" + r + r"\s*=>", l):
                return True
    return False


def _assigned_rhs(lines, i, name, py):
    pat = re.compile((r"^\s*" if py else r"\b(?:const|let|var)\s+") + re.escape(name) + r"\s*=(?!=)\s*(.*)")
    for k in range(i, max(0, i - 40) - 1, -1):
        m = pat.search(lines[k]) if not py else pat.match(lines[k])
        if m:
            return m.group(1)
    return None


_FILE = {"offline": False, "src": ""}
_INGRESS = re.compile(r"\bfetch\s*\(|XMLHttpRequest|\$\.(?:get|ajax|getJSON)|axios|JSON\.parse|\.json\(\)|WebSocket|"
                      r"EventSource|localStorage|sessionStorage|location\.(?:search|hash)|URLSearchParams")


def _is_data(expr, lines, i, py):
    """expr carries untrusted-looking data: data-ish by name/key, and a plain variable is judged by what it was
    assigned from (constants, translation tables and built HTML strings are not data)."""
    dat = _py_dataish if py else _dataish
    if _local_safe(lines, i, expr, py):
        return False
    if not py and _FILE["offline"]:
        # no fetch/JSON ingress in this file: a `key:` literal in an in-file data array means the value is hardcoded
        m = re.fullmatch(r"[A-Za-z_$][\w$]*\.([A-Za-z_$][\w$]*)", expr.strip())
        if m and re.search(r"\b" + re.escape(m.group(1)) + r"\s*:\s*[\"'`]", _FILE["src"]):
            return False
    e = expr.strip()
    if re.fullmatch(r"[A-Za-z_$][\w$]*", e):
        rhs = _assigned_rhs(lines, i, e, py)
        if rhs is not None:
            rhs = rhs.rstrip(";").strip()
            if CONST_ROOT.match(_root(rhs)) or _root(rhs).lower() in STATIC_ROOTS or "`" in rhs \
                    or rhs.startswith(("<", "'<", '"<')):
                return False
            return dat(rhs)
    return dat(expr)


# ---------------------------------------------------------------- JS / HTML
JS_SINK = re.compile(r"(?:\.|\b)(innerHTML|outerHTML)\s*(\+?=)(?!=)|\binsertAdjacentHTML\s*\(|\bdocument\.write(?:ln)?\s*\(")
DANGEROUS = re.compile(r"dangerouslySetInnerHTML\s*=\s*\{\{?\s*__html\s*:\s*([^}\n]+)")
MD_LIB = re.compile(r"\b(?:marked(?:\.parse)?|markdownit|md\.render|markdown\.render|showdown|snarkdown|mdToHtml|"
                    r"renderMarkdown|markdownToHtml|md2html)\s*\(|\bmarked\.parse\(|\bmarked\.parseInline\(|"
                    r"new\s+showdown\.Converter")


def _statement(lines, i, col):
    """Text of the JS statement starting at lines[i][col:], through the closing ';' (bracket and template aware)."""
    buf, depth, stack = [], 0, []   # stack of open string kinds: "`", "'", '"', "${"
    for k in range(i, min(i + 60, len(lines))):
        s = lines[k][col:] if k == i else lines[k]
        j = 0
        while j < len(s):
            ch = s[j]
            top = stack[-1] if stack else ""
            if top in ("'", '"'):
                if ch == "\\":
                    j += 1
                elif ch == top:
                    stack.pop()
            elif top == "`":
                if ch == "\\":
                    j += 1
                elif ch == "`":
                    stack.pop()
                elif ch == "$" and s[j + 1:j + 2] == "{":
                    stack.append("${"); j += 1
            else:
                if ch in "'\"`":
                    stack.append(ch)
                elif ch in "([{":
                    depth += 1
                    if ch == "{" and top == "${":
                        pass
                elif ch in ")]}":
                    if ch == "}" and top == "${":
                        stack.pop()
                    else:
                        depth -= 1
                elif ch == ";" and not stack and depth <= 0:
                    buf.append(s[:j])
                    return "\n".join(buf), k
                elif ch == "/" and s[j + 1:j + 2] == "/" and not stack:
                    s = s[:j]; break
            j += 1
        buf.append(s)
        if not stack and depth <= 0 and k > i and not s.rstrip().endswith((",", "+", "(", "=", "?", ":", "&&", "||")):
            # no semicolon (ASI style): stop at a balanced line
            return "\n".join(buf), k
        if not stack and depth <= 0 and k == i and s.strip() and not s.rstrip().endswith((",", "+", "(", "=", "?", ":", "&&", "||", "`")):
            return "\n".join(buf), k
    return "\n".join(buf), min(i + 59, len(lines) - 1)


def _template_exprs(text):
    """Yield (offset, expr_without_nested_templates) for every ${...} in text (nested ones yielded separately)."""
    out, j = [], 0
    while True:
        j = text.find("${", j)
        if j < 0:
            return out
        depth, k = 1, j + 2
        while k < len(text) and depth:
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
            k += 1
        raw = text[j + 2:k - 1]
        flat = re.sub(r"`(?:[^`$\\]|\\.|\$(?!\{))*`", "``", raw)          # drop literal nested templates
        flat = re.sub(r"`[^`]*\$\{.*\}[^`]*`", "``", flat, flags=re.S)       # nested templates holding ${...}
        out.append((j, flat))
        j += 2


def _js_dynamic(stmt: str, lines=None, i=0):
    """Return the first unescaped data-ish interpolated expression in a JS HTML-building statement, else None."""
    for off, ex in _template_exprs(stmt):
        if _is_data(ex, lines, min(i + stmt[:off].count("\n"), len(lines) - 1), False) if lines else _dataish(ex):
            return ex.strip()
    # string concatenation: '<td>' + x.text + '</td>'
    no_tpl = re.sub(r"`(?:[^`\\]|\\.)*`", "``", stmt, flags=re.S)
    for m in re.finditer(r"[\"']\s*\+\s*([A-Za-z_$][\w$.\[\]'\"()]*)", no_tpl):
        if _is_data(m.group(1), lines, i, False) if lines else _dataish(m.group(1)):
            return m.group(1)
    return None


HTML_CTX = re.compile(r"<[A-Za-z][^>]*\$\{|>\s*\$\{|\$\{[^}]*\}\s*</?[A-Za-z]|=\s*[\"']?\$\{")


def _scan_js_templates(rel, lines, hits, done):
    """HTML built in template literals / helper functions that are later assigned to innerHTML."""
    for i, line in enumerate(lines):
        if i in done or "${" not in line or len(line) > 3000 or not HTML_CTX.search(line):
            continue
        for _, ex in _template_exprs(line):
            if _is_data(ex, lines, i, False):
                done.add(i)
                hits.append(Hit(rel, i + 1, snippet(line), f"HTML template literal interpolates unescaped value `{ex.strip()[:60]}` "
                                f"(file assigns HTML via innerHTML/insertAdjacentHTML)"))
                break


def _scan_js(repo, rel, lines, hits):
    done = set()
    for i, line in enumerate(lines):
        if len(line) > 3000 or "DOMPurify" in line and "marked" not in line and "innerHTML" not in line:
            continue
        m = JS_SINK.search(line)
        if m:
            sink = m.group(1) or m.group(0).strip("( ")
            stmt, end = _statement(lines, i, m.end())
            rhs = stmt.strip()
            if not rhs or re.fullmatch(r"[\"'`]\s*[\"'`]|null|undefined", rhs):
                continue
            ctx = "\n".join(lines[max(0, i - 3):end + 1])
            is_md = MD_LIB.search(rhs) or (re.fullmatch(r"[\w$.]+", rhs) and re.search(
                r"(?:const|let|var)\s+" + re.escape(rhs) + r"\s*=\s*(?:await\s+)?[^;\n]*\b(?:marked|markdownit|md\.render|showdown)", "\n".join(lines[max(0, i - 15):i + 1])))
            if is_md:
                if "DOMPurify" in rhs or "sanitize" in rhs.lower():
                    if re.search(r"FORBID_TAGS[^\n]*img|ALLOWED_TAGS|ALLOWED_URI_REGEXP|FORBID_ATTR[^\n]*src|ADD_URI_SAFE", ctx):
                        continue
                    hits.append(Hit(rel, i + 1, snippet(line),
                                    f"{sink}: Markdown sanitised with DOMPurify default config - remote <img>/links survive "
                                    f"(data exfiltration via image URL; lower severity than raw HTML)"))
                else:
                    hits.append(Hit(rel, i + 1, snippet(line), f"{sink} receives rendered Markdown with no DOMPurify sanitisation"))
                continue
            if "DOMPurify" in rhs or ESCAPER.fullmatch(rhs.split("(")[0] + "(") and rhs.startswith(("esc", "sanitize")):
                continue
            dyn = _js_dynamic(rhs, lines, i)
            if dyn is None and re.fullmatch(r"[\w$.\[\]'\"]+", rhs) and not rhs[0] in "\"'`" and _is_data(rhs, lines, i, False):
                dyn = rhs
            if dyn:
                done.update(range(i, end + 1))
                hits.append(Hit(rel, i + 1, snippet(line),
                                f"{sink} built from unescaped value `{dyn[:60]}`"))
            continue
        m = DANGEROUS.search(line)
        if m:
            arg = m.group(1).strip()
            if not (re.match(r"[\"'`]", arg) or ESCAPER.search(arg) or "sanitize" in arg.lower()):
                if MD_LIB.search(arg) or _dataish(arg) or re.fullmatch(r"[\w$.]+", arg):
                    hits.append(Hit(rel, i + 1, snippet(line), f"dangerouslySetInnerHTML with unsanitised `{arg[:50]}`"))
    if any(JS_SINK.search(l) for l in lines):
        _scan_js_templates(rel, lines, hits, done)


# ---------------------------------------------------------------- Python / Jinja
HTML_TAGS = (r"(?:div|span|td|th|tr|li|ul|ol|p|h[1-6]|a|b|i|em|strong|code|pre|table|tbody|thead|small|label|section|"
             r"details|summary|button|option|blockquote|title|body|dd|dt|mark|u|sup|sub|figcaption|caption)")
PY_FSTR_HTML = re.compile(r"""\b[fF][rR]?["']|\b[rR]?[fF]["']|\.format\(""")
HTML_TAG_EXPR = re.compile(r"<" + HTML_TAGS + r"(?:\s[^<>{}]*)?>\s*\{|\}\s*</" + HTML_TAGS + r"\s*>|"
                           r"<" + HTML_TAGS + r"\s[^<>]*=\s*[\"']\{", re.I)
ST_CALL = re.compile(r"\bst\.(markdown|write|html|caption)\s*\(|\bcomponents\.html\s*\(|\bgr\.HTML\s*\(|"
                     r"\bMarkup\s*\(|\bmark_safe\s*\(")
PY_ESC = re.compile(r"\b_?esc\w*\(|\bhtml\.escape\(|\bescape\(|\bquote\(|\bbleach\.|\bsanitiz\w*\(|\b_?h\(|"
                    r"\bjson\.dumps\(|\bMarkup\.escape\(|\|\s*e\b|\|\s*escape\b|\bsafe_\w+\(")
JINJA_SAFE = re.compile(r"\{\{\s*([^}|]+?)\s*\|\s*safe\s*\}\}")
AUTOESC_OFF = re.compile(r"autoescape\s*=\s*(?:False|false)\b")
PY_JOIN = re.compile(r"^\s*(?:\"\"|\'\'|\"[^\"]*\"|\'[^\']*\')\s*\.join\(")


def _py_exprs(text):
    """Return expressions inside f-string braces ({{ and }} are literal braces)."""
    t = text.replace("{{", "\0\0").replace("}}", "\1\1")
    out, j = [], 0
    while True:
        j = t.find("{", j)
        if j < 0:
            return out
        depth, k = 1, j + 1
        while k < len(t) and depth:
            depth += (t[k] == "{") - (t[k] == "}")
            k += 1
        out.append(t[j + 1:k - 1])
        j = k


def _py_dataish(expr: str) -> bool:
    e = _strip_cond(expr.strip(), True)
    if not e or PY_ESC.search(e) or NUMERIC.search(e) or ERRVAR.match(e) or PY_JOIN.match(e):
        return False
    if re.match(r"^(?:render|build|make|format|fmt)\w*\(", e):
        return False
    if re.fullmatch(r"[\w.]+\(\s*(?:[\"'][^\"']*[\"']\s*,?\s*)*\)", e) and not re.search(r"\.get\(|\bgetattr\(", e):
        return False
    keys = re.findall(r"(?:\[\s*|\.get\(\s*)[\"']([A-Za-z_][\w ]*)[\"']", e)
    e2 = re.sub(r"\"[^\"]*\"|'[^']*'", "''", e)
    toks = keys + re.findall(r"[A-Za-z_]\w*(?!\w|\s*\()", e2)
    return any(w in WORDS and not any(g in GENERATED for g in _words(t.replace(" ", "_")))
               for t in toks for w in _words(t.replace(" ", "_")))


def _py_call(lines, i, col):
    depth, buf = 0, []
    for k in range(i, min(i + 40, len(lines))):
        s = lines[k][col:] if k == i else lines[k]
        buf.append(s)
        depth += s.count("(") - s.count(")")
        if depth <= 0:
            break
    return "\n".join(buf)


def _py_bare_ok(lines, i, e):
    """Bare names (no subscript / .get / attribute data access) are only trusted-tainted if assigned from data."""
    return _local_safe(lines, i, e, True)


def _scan_py(repo, rel, lines, hits):
    src = repo.read(rel)
    if re.search(r"\bimport\s+reportlab|from\s+reportlab|\bfpdf\b|\bdocx\b", src):
        pdf_like = True
    else:
        pdf_like = False
    for i, l in enumerate(lines):
        if AUTOESC_OFF.search(l) and not l.lstrip().startswith("#"):
            hits.append(Hit(rel, i + 1, snippet(l), "Jinja autoescape disabled: template variables are inserted unescaped"))
    seen = set()
    is_st = "streamlit" in src or "gradio" in src
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        m = ST_CALL.search(line)
        if m:
            sink = m.group(0).rstrip("( ")
            raw_sink = sink.startswith(("gr.HTML", "Markup", "mark_safe", "components.html", "st.html"))
            if sink.startswith("st.") and not is_st:
                continue
            call = _py_call(lines, i, m.start())
            unsafe = "unsafe_allow_html=True" in call.replace(" ", "")
            if PY_FSTR_HTML.search(call):
                dyn = next((e for e in _py_exprs(call) if _is_data(e, lines, i, True)), None)
            else:
                arg = call[m.end() - m.start():].split(",")[0].strip().rstrip(")")
                dyn = arg if (raw_sink or unsafe) and re.fullmatch(r"[A-Za-z_][\w.\[\]'\"]*", arg) and _is_data(arg, lines, i, True) else None
            if dyn and i not in seen:
                seen.add(i)
                if unsafe or raw_sink:
                    why = f"{sink}() renders HTML with unescaped value `{dyn.strip()[:60]}`"
                else:
                    why = (f"{sink}() renders model/record text `{dyn.strip()[:60]}` as Markdown: injected ![](https://attacker/?q=..) "
                           f"or links are rendered (exfiltration; lower severity than raw HTML)")
                hits.append(Hit(rel, i + 1, snippet(line), why))
            continue
        if not pdf_like and PY_FSTR_HTML.search(line) and HTML_TAG_EXPR.search(line):
            for e in _py_exprs(line):
                if _is_data(e, lines, i, True):
                    if i not in seen:
                        seen.add(i)
                        hits.append(Hit(rel, i + 1, snippet(line), f"HTML f-string interpolates unescaped value `{e.strip()[:60]}`"))
                    break


def _scan_template(rel, lines, hits):
    for i, l in enumerate(lines):
        m = JINJA_SAFE.search(l)
        if m and _py_dataish(m.group(1)) and _root(m.group(1)).lower() not in STATIC_ROOTS:
            hits.append(Hit(rel, i + 1, snippet(l), f"Jinja `|safe` disables escaping for `{m.group(1).strip()[:50]}`"))


def run(repo):
    hits = []
    for rel in repo.files(EXTS):
        low = rel.lower()
        if low.endswith((".min.js", ".bundle.js")) or "/vendor/" in low or "/lib/" in low and low.endswith(".js") and "min" in low:
            continue
        src = repo.read(rel)
        if not src or not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|dangerouslySetInnerHTML|"
                                    r"unsafe_allow_html|\|\s*safe|Markup|mark_safe|autoescape|<[a-zA-Z]|gr\.HTML|st\.(?:markdown|write)|"
                                    r"components\.html|HTMLResponse", src):
            continue
        lines = src.splitlines()
        _FILE["offline"] = not _INGRESS.search(src)
        _FILE["src"] = src
        before = len(hits)
        if low.endswith(".py"):
            _scan_py(repo, rel, lines, hits)
            if re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|dangerouslySetInnerHTML", src):
                _scan_js(repo, rel, lines, hits)    # JS embedded in a Python-served HTML string
        else:
            if low.endswith((".html", ".htm", ".j2", ".jinja")):
                _scan_template(rel, lines, hits)
            _scan_js(repo, rel, lines, hits)
    return hits
