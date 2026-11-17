"""SAAF-007: a URL / repository location supplied by the caller (HTTP request, form field, UI text box, LLM tool
argument) reaches an outbound fetch or `git clone` without a scheme + host allowlist.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, functions, snippet

CHECK = {
    "id": "SAAF-007",
    "slug": "user-controlled-url-fetch",
    "category": "ssrf",
    "severity": "Medium",
    "title": "User-supplied URL or repository location is fetched or cloned server-side without a scheme/host allowlist",
    "intended": "The service fetches or clones only from a small, known set of public hosts (for example github.com over "
                "https, or one configured update URL).",
    "actual": "A value taken from the request (JSON body, query string, form field, UI text box or LLM tool argument) is "
              "passed unchanged to an HTTP client (requests/httpx/aiohttp/urllib.urlopen/fetch) or to `git clone` / "
              "subprocess; the code path has no scheme and host allowlist, no private/loopback/link-local address "
              "block, and `git clone` is called without `--` before the URL so a value starting with '-' is parsed as "
              "a git option.",
    "impact": "Anyone who can reach the endpoint (or can influence the LLM tool call) makes the server request internal "
              "services, cloud metadata addresses, file:// paths or local repositories; error text or fetched content "
              "is usually returned, giving a response oracle and data disclosure. An option-like value (for example "
              "--upload-pack=...) can turn git clone into command execution.",
    "recommendation": "Parse the value with urllib.parse.urlsplit, require scheme https and a host from an explicit "
                      "allowlist, resolve the host and reject loopback/private/link-local/metadata addresses, disable "
                      "redirects (or re-validate each hop), set size and time limits, and do not echo raw error text. "
                      "For git use `git clone --depth 1 -- <url> <dir>` (with `-c protocol.allow=never -c "
                      "protocol.https.allow=always`) after validating the URL. Prefer fixed server-side URLs over "
                      "caller-supplied ones.",
    "refs": "CWE-918, CWE-88, OWASP LLM06 (Excessive Agency), OWASP A10:2021",
}

# ---- sources -------------------------------------------------------------------------------------------------------
URLISH = r"(?:url|uri|link|repo|endpoint|host|site|href|remote|source|feed|webhook)"
SRC_REQ = re.compile(
    r"\brequest\.(?:get_json|json|args|form|values|data|files|GET|POST|query_params|path_params)\b|"
    r"\brequest\.(?:get|post)\.get\(|\bst\.(?:text_input|text_area|chat_input)\(|\bflask\.request\.|"
    r"\b(?:await\s+)?request\.(?:json|form|body)\(\)|"
    r"\b(?:tool_input|tool_args|tool_arguments|arguments|args|params|kwargs|payload|inputs?)"
    r"(?:\[\s*[\"'][\w-]*" + URLISH + r"[\w-]*[\"']\s*\]|\.get\(\s*[\"'][\w-]*" + URLISH + r"[\w-]*[\"'])", re.I)
ROUTE_DEC = re.compile(r"^\s*@\s*[\w.]+\.(?:route|get|post|put|delete|patch|api_route|websocket)\s*\(")
TOOL_DEC = re.compile(r"^\s*@\s*(?:[\w.]+\.)?(?:tool|function_tool|kernel_function|mcp_tool)\b")
DEF_SIG = re.compile(r"(?:async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(?:->[^:]+)?:", re.S)
URL_PARAM = re.compile(r"^(?:\w*_)?" + URLISH + r"\w*$", re.I)
FASTAPI_ANN = re.compile(r":\s*(?:Annotated\[[^=]*)?(?:Form|Query|Body)\b")
ASSIGN = re.compile(r"^\s*(?:self\.)?(\w+)\s*(?::[^=\n]+)?=(?!=)\s*(.+)$")

# ---- sinks ---------------------------------------------------------------------------------------------------------
HTTP_SINK = re.compile(
    r"\b(?:requests|httpx|http|session|sess|client|aiohttp|s|c|self\.session|self\.client|self\.http)\.(?:get|post|put|"
    r"patch|delete|head|request|stream|fetch|urlopen)\s*\(|\burlopen\s*\(|\burlretrieve\s*\(|\bfetch\s*\(|"
    r"\baxios(?:\.(?:get|post|put|request))?\s*\(|\bgot(?:\.get|\.post)?\s*\(|\burllib\.request\.Request\s*\(|"
    r"\bRequest\s*\(|\bClientContext\s*\(")
GIT_SINK = re.compile(r"\b(?:subprocess\.\w+|Popen|check_output|check_call|run|os\.system|os\.popen|execSync|exec|"
                      r"spawn(?:Sync)?|sh\.git|git\.Git\(\)\.clone|Repo\.clone_from|clone_from|porcelain\.clone)\s*\(")
GUARD = re.compile(r"urlparse|urlsplit|\.hostname|\.netloc|ipaddress|is_private|is_loopback|allow_?list|allowed_?hosts?|"
                   r"white_?list|allowed_?(?:domains?|urls?|origins?|schemes?)|validate_url|validate_repo|is_safe|safe_url|is_valid_url|gethostbyname|"
                   r"getaddrinfo|ssrf|\w*(?:validate|check_url|sanitize|verify_url|ensure_safe|ensure_allowed)\w*\(|new URL\(|isAllowed|url_is_allowed", re.I)


def _balanced(text, start):
    """Return the text inside the parenthesis that opens at text[start] (best effort)."""
    depth = 0
    for i in range(start, min(len(text), start + 1500)):
        ch = text[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return text[start + 1:start + 600]


def _split_args(s):
    out, depth, cur, q = [], 0, [], None
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    out.append("".join(cur).strip())
    return [a for a in out if a]


def _params(lines, a):
    m = DEF_SIG.search("\n".join(lines[a:a + 20]))
    if not m:
        return []
    res = []
    for p in _split_args(m.group(2)):
        name = re.match(r"\*{0,2}(\w+)", p)
        if name and name.group(1) not in ("self", "cls", "request", "response", "req", "res"):
            res.append((name.group(1), p))
    return res


def _decorators(lines, a):
    j = a - 1
    decs = []
    while j >= 0 and lines[j].lstrip().startswith("@"):
        decs.append(lines[j])
        j -= 1
    return decs


def _tainted_vars(body_lines, seeds, route_params):
    """Single forward pass(es) of assignment propagation. Returns set of tainted variable names."""
    tv = set(seeds)
    extra = None
    if route_params:
        extra = re.compile(r"\b(?:%s)\.\w*%s\w*" % ("|".join(map(re.escape, route_params)), URLISH), re.I)
    for _ in range(3):
        for l in body_lines:
            m = ASSIGN.match(l)
            if not m or l.lstrip().startswith("#"):
                continue
            lhs, rhs = m.group(1), m.group(2)
            if re.match(r"\s*(?:int|float|bool|len|json\.dumps)\(", rhs):
                continue
            if _expr_tainted(rhs, tv, extra):
                tv.add(lhs)
    return tv, extra


def _expr_tainted(expr, tv, extra):
    if SRC_REQ.search(expr) or (extra and extra.search(expr)):
        return True
    return any(re.search(r"(?<![\w.\"'])%s\b" % re.escape(v), expr) for v in tv)


def _url_arg_tainted(arg, tv, extra):
    """Whole URL (or its host/prefix) is attacker-controlled: bare tainted expr, or f-string/concat starting with it."""
    a = arg.strip()
    if a.startswith("url=") or a.startswith("uri="):
        a = a.split("=", 1)[1].strip()
    if re.match(r"^[A-Za-z_]\w*\s*=", a):
        return False
    core = re.sub(r"^(?:str|\w+\.strip|\w+\.rstrip)\(", "", a)
    if re.match(r"^f[\"']\s*\{", a):
        return _expr_tainted(re.match(r"^f[\"']\s*\{([^}]*)\}", a).group(1), tv, extra)
    if re.match(r"^f?[\"']", a):
        return False
    first = re.split(r"\s*\+\s*", core)[0]
    return _expr_tainted(first, tv, extra) and not re.search(r"\b(?:int|len)\(", first)


def _sink_calls(body_text):
    """Yield (offset, kind, arg_list) for HTTP/git sinks."""
    for m in HTTP_SINK.finditer(body_text):
        args = _split_args(_balanced(body_text, m.end() - 1))
        if args:
            yield m.start(), "http", args
    for m in GIT_SINK.finditer(body_text):
        inner = _balanced(body_text, m.end() - 1)
        if re.search(r"[\"']clone[\"']|git\s+clone|clone_from|\.clone\(", body_text[m.start():m.end() + len(inner) + 2]):
            yield m.start(), "git", [inner]


def _git_has_dashdash(inner):
    return bool(re.search(r"[\"']--[\"']", inner))


def _analyse(lines, a, b, seeds, route_params):
    """Return list of (line_idx, kind, tainted_names_used, arg_text) of unguarded sinks fed by tainted data."""
    body_lines = lines[a:b]
    body = "\n".join(body_lines)
    tv, extra = _tainted_vars(body_lines, seeds, route_params)
    out = []
    for off, kind, args in _sink_calls(body):
        ln = a + body.count("\n", 0, off)
        if kind == "http":
            cand = args[0] if not args[0].lower().startswith(("method", "'get'", '"get"')) else ""
            if re.match(r"^[\"'](?:GET|POST|PUT|DELETE|PATCH|HEAD)[\"']$", args[0], re.I) and len(args) > 1:
                cand = args[1]
            for a_ in args:
                if re.match(r"^url\s*=", a_):
                    cand = a_
            if cand and _url_arg_tainted(cand, tv, extra):
                out.append((ln, kind, cand))
        else:
            inner = args[0]
            words = set(re.findall(r"[A-Za-z_]\w*", inner)) & tv
            direct = SRC_REQ.search(inner) or (extra and extra.search(inner))
            if (words or direct) and not _git_has_dashdash(inner):
                out.append((ln, kind, inner))
    return out, tv, extra, body


def _file_functions(repo):
    for rel in repo.files({".py"}):
        text = repo.read(rel)
        if not re.search(r"clone|urlopen|requests|httpx|aiohttp|urllib|fetch|http", text):
            continue
        lines = repo.lines(rel)
        for a, b, head in functions(lines):
            yield rel, lines, a, b, head


def run(repo):
    funcs = list(_file_functions(repo))
    # pass 1: helper functions that forward one of their own parameters to a sink (no guard in the helper)
    sink_helpers = {}   # name -> set(param index)
    for rel, lines, a, b, head in funcs:
        m = DEF_SIG.search("\n".join(lines[a:a + 20]))
        if not m:
            continue
        plist = [p for p in _split_args(m.group(2)) if re.match(r"\*{0,2}\w+", p)]
        names = [re.match(r"\*{0,2}(\w+)", p).group(1) for p in plist]
        idxs = set()
        for i, n in enumerate(names):
            if n in ("self", "cls"):
                continue
            hits, _, _, body = _analyse(lines, a + 1, b, {n}, [])
            if hits and not GUARD.search(body):
                idxs.add(i - (1 if names and names[0] in ("self", "cls") else 0))
        if idxs:
            sink_helpers[m.group(1)] = idxs

    hits, seen = [], set()
    for rel, lines, a, b, head in funcs:
        decs = _decorators(lines, a)
        is_route = any(ROUTE_DEC.match(d) for d in decs)
        is_tool = any(TOOL_DEC.match(d) for d in decs)
        seeds, route_params = set(), []
        for name, raw in _params(lines, a):
            if is_route and (URL_PARAM.match(name) or FASTAPI_ANN.search(raw)) and not re.search(r":\s*(?:int|bool|float)\b", raw):
                seeds.add(name)
            elif is_route and re.search(r":\s*[A-Z]\w+", raw) and not re.search(r":\s*(?:str|int|bool|float|Request)\b", raw):
                route_params.append(name)      # pydantic body model: body.url etc.
            if is_tool and URL_PARAM.match(name):
                seeds.add(name)
        found, tv, extra, body = _analyse(lines, a + 1, b, seeds, route_params)
        guarded = bool(GUARD.search(body))
        for ln, kind, arg in found:
            if guarded:
                continue
            if (rel, ln) in seen:
                continue
            seen.add((rel, ln))
            what = "git clone" if kind == "git" else "outbound HTTP request"
            hits.append(Hit(rel, ln + 1, snippet(lines[ln]),
                            f"{head[:60]}: request/tool-supplied value reaches {what} with no scheme/host allowlist"
                            + ("" if kind == "http" else " and no `--` before the URL")))
        # calls to helpers that forward a parameter to a sink
        if guarded or not (tv or extra):
            continue
        for name, idxs in sink_helpers.items():
            for i in range(a + 1, b):
                m = re.search(r"(?<![\w.])(?:self\.|\w+\.)?%s\s*\(" % re.escape(name), lines[i])
                if not m or lines[i].lstrip().startswith(("def ", "async def ")):
                    continue
                call_args = _split_args(_balanced("\n".join(lines[i:i + 6]), lines[i].index("(", m.start())))
                for k in idxs:
                    if k < len(call_args) and _expr_tainted(re.sub(r"^\w+\s*=\s*", "", call_args[k]), tv, extra) \
                            and not re.match(r"^f?[\"']", call_args[k]):
                        if (rel, i) not in seen:
                            seen.add((rel, i))
                            hits.append(Hit(rel, i + 1, snippet(lines[i]),
                                            f"{head[:50]}: request-supplied value passed to {name}(), which fetches/clones "
                                            f"it without a scheme/host allowlist"))
    hits.extend(_js_hits(repo))
    return hits


# ---- JavaScript / TypeScript (very small subset: req.body/query value used directly as the fetch target) ------------
JS_SRC = re.compile(r"\b(?:req|request)\.(?:body|query|params)(?:\.(\w+)|\[[\"'](\w+)[\"']\])")
JS_ASSIGN = re.compile(r"\b(?:const|let|var)\s+(?:\{\s*([^}]+)\}|(\w+))\s*=\s*(?:await\s+)?(?:req|request)\.(?:body|query|params)\b")
JS_SINK = re.compile(r"\b(?:fetch|axios(?:\.\w+)?|got|request|http\.get|https\.get|urlopen)\s*\(\s*([^,)\s][^,)]*)")


def _js_hits(repo):
    out = []
    for rel in repo.files({".js", ".ts", ".mjs", ".cjs"}):
        text = repo.read(rel)
        if not re.search(r"\b(?:req|request)\.(?:body|query|params)", text) or GUARD.search(text):
            continue
        tv = set()
        for m in JS_ASSIGN.finditer(text):
            for n in (m.group(1) or m.group(2) or "").split(","):
                n = n.split(":")[-1].strip()
                if n:
                    tv.add(n)
        for m in re.finditer(r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:req|request)\.(?:body|query|params)(?:\.\w+|\[[^\]]+\])", text):
            tv.add(m.group(1))
        for i, l in enumerate(repo.lines(rel)):
            m = JS_SINK.search(l)
            if not m:
                continue
            arg = m.group(1).strip()
            if arg[:1] in "\"'`":
                continue
            if JS_SRC.match(arg) or arg in tv:
                out.append(Hit(rel, i + 1, snippet(l), "request-supplied value used as the fetch target with no host allowlist"))
    return out
