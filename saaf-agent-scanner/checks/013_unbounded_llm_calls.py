"""SAAF-013: LLM calls, agent/retry loops, outbound LLM HTTP calls and LLM-triggering web endpoints without limits, plus
regexes with catastrophic backtracking that run over untrusted documents.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, functions, snippet

CHECK = {
    "id": "SAAF-013",
    "slug": "unbounded-llm-calls",
    "category": "resource-exhaustion-no-limits",
    "severity": "Low",
    "title": "LLM calls, loops or regexes run without limits (no iteration cap, timeout, input size cap or rate limit)",
    "intended": "Every LLM call, agent/retry loop and document-parsing regex is bounded in time, iterations, input size "
                "and request rate, so a single request or a single hostile document cannot consume unlimited compute, "
                "memory or paid API budget.",
    "actual": "The code contains at least one of: a regex with nested or adjacent unbounded quantifiers (catastrophic "
              "backtracking); a while-True / agent / polling loop around an LLM call with no max iterations, deadline or "
              "budget; a raw HTTP call to an LLM API without a timeout; or a web endpoint that calls an LLM with no "
              "rate limiting in the repository and no input size cap.",
    "impact": "One crafted document (e.g. an unterminated '<!--') can pin a worker or the Node event loop for minutes to "
              "hours; a stuck or looping agent burns tokens indefinitely; an unauthenticated or unthrottled endpoint lets "
              "anyone exhaust the operator's LLM budget (denial of wallet) or memory and block other users.",
    "recommendation": "Cap loop iterations and wall-clock time (max_turns/max_iterations, deadline, retry budget with "
                      "backoff); set explicit timeouts on every LLM client and HTTP call; enforce request/upload size and "
                      "per-field length limits before parsing or prompting; add per-user/IP rate limits and a spend "
                      "budget; replace nested/adjacent unbounded regex quantifiers with bounded or linear-time forms "
                      "(bounded repeats, str.find for fixed markers, a regex engine with timeouts) and cap input length.",
    "refs": "CWE-1333, CWE-400, CWE-770, CWE-835, OWASP LLM10",
}

CODE = {".py", ".js", ".ts", ".tsx", ".mjs", ".cjs", ".jsx"}

# ---------------------------------------------------------------- shared
LLM_CALL = re.compile(
    r"\.messages\.(?:create|stream)\(|\.chat\.completions\.(?:create|parse)\(|\.responses\.create\(|"
    r"\.beta\.messages\.\w+\(|\bgenerate_content(?:_async)?\(|\.generateContent\(|\bgenerateContent\(|"
    r"\b(?:llm|chain|model|agent|chat|client)\w*\.(?:invoke|ainvoke|predict|run_sync)\(|"
    r"\b(?:litellm|ollama)\.(?:a?completion|chat)\(|\bgenerateText\(|\bstreamText\(|"
    r"api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis|openai\.azure\.com|/chat/completions|"
    r"\.batches\.create\(|\.converse\(|invoke_model\(")
LLM_SDK = re.compile(r"\banthropic\b|\bopenai\b|langchain|litellm|ollama|google\.generativeai|\bgenai\b|bedrock|"
                     r"@ai-sdk|from ['\"]ai['\"]", re.I)


def _comment(line):
    return line.lstrip().startswith(("#", "//", "*", "/*"))


# ---------------------------------------------------------------- (1) ReDoS
# A "wildcard token" is an unbounded repeat of something that can match almost anything.
_W = (r"(?:\.[*+]\??|\[\\s\\S\][*+]\??|\[\\S\\s\][*+]\??|\[\^[^\]\n]{0,12}\][*+]\??|"
      r"\(\?:\(\?!(?:[^()\n]|\([^()\n]*\))*\)(?:\.|\[\\s\\S\]|\[\\S\\s\]|\[\^\]\])\)[*+]\??)")
REDOS = [
    # (a+)+  (.*)*  (?:x*)*  (\w+\s*)*
    (re.compile(r"\((?:\?:)?(?:(?:\\.|\[[^\]\n]*\]|\.|[A-Za-z0-9_])[*+]\??){1,3}\)[*+{]"), "nested quantifier (x*)*"),
    # (\s|.)*?  (.|\n)*  ([\s\S]|.)+  (a|a)* style overlapping alternation under a quantifier
    (re.compile(r"\((?:\?:)?(?:\.\||[^()\n]*\|\.)[^()\n]*\)[*+]"), "overlapping alternation with '.' under a quantifier"),
    (re.compile(r"\((?:\?:)?(?:\\s\|\\S|\\S\|\\s|\\d\|\\w|\\w\|\\d|\\s\|\\s|\\w\|\\w)\)[*+]"), "overlapping alternation under a quantifier"),
    # two adjacent unbounded wildcards: [^>]*.*?-->   .*.*   (?:(?!-->)[\s\S])*?X(?:(?!-->)[\s\S])*?
    (re.compile(_W + _W), "adjacent unbounded wildcards"),
    (re.compile(r"\(\?:\(\?![^\n]{0,40}?\)(?:\.|\[\\s\\S\]|\[\\S\\s\])\)\*\?(?:\[[^\]\n]{1,20}\]\{\d+,\}|[^()*+?\n]{1,12})"
                r"\(\?:\(\?![^\n]{0,40}?\)(?:\.|\[\\s\\S\]|\[\\S\\s\])\)\*\?"), "two lazy tempered wildcards around a short atom"),
]
_REGEX_CTX = re.compile(r"\bre\.\w+\(|RegExp\(|\br[\"']|\.(?:test|match|matchAll|replace|replaceAll|search|exec|split)\(|"
                        r"(?:^|[=(:,\s])/[^/\s]|compile\(|PATTERN|REGEX|_RE\b", re.I)


def _redos(repo):
    out = []
    for rel in repo.files(CODE):
        for i, line in enumerate(repo.lines(rel)):
            if len(line) > 600 or _comment(line) or not _REGEX_CTX.search(line):
                continue
            for rx, why in REDOS:
                if rx.search(line):
                    out.append(Hit(rel, i + 1, snippet(line), f"catastrophic-backtracking regex: {why}"))
                    break
    return out


# ---------------------------------------------------------------- (2) loops
LOOP = re.compile(r"^\s*(?:while\s+(?:True|1)\s*:|while\s*\(\s*(?:true|1)\s*\)|for\s*\(\s*;\s*;\s*\)|"
                  r"while\s+.*(?:stop_reason|tool_calls|tool_use|finish_reason|\.status\b|processing_status|"
                  r"\bnot\s+(?:done|finished|complete)\w*)\b.*:\s*$|"
                  r"for\s+\w+\s+in\s+itertools\.count\(\))")
BOUND = re.compile(r"(?i:max_?(?:turns|iter\w*|steps|tries|retries|attempts|rounds|loops|calls|depth|wait|elapsed))|MAX_[A-Z_]+|"
                   r"attempt|retries|\btries\b|\bretry_count|\bn_?calls\b|deadline|monotonic|time\.time\(\)\s*[-<>]|"
                   r"Date\.now\(\)\s*[-<>]|elapsed|budget|\bturns?\b\s*(?:[<>]=?|\+=)|\bstep\w*\s*(?:[<>]=?|\+=)|"
                   r"\biteration\w*\s*(?:[<>]=?|\+=)|\bcount\w*\s*(?:[<>]=?|\+=)|\bi\s*(?:[<>]=?|\+=)\s*\d|"
                   r"\bwait_for\b|asyncio\.timeout|signal\.alarm|timeout\s*[<>=]|\bstop_event\b|\.is_set\(\)")
INTERACTIVE = re.compile(r"\binput\(|chat_input|readline|\bqueue\b|\.recv\(|\.receive|\.accept\(|\.poll\(|consumer|"
                         r"\.get\(\s*(?:timeout|block)|serve_forever|websocket|\bawait\s+\w+\.read\(|"
                         r"prompt\(|readline\.createInterface|schedule\.run_pending", re.I)


def _block(lines, i):
    """Return (start, end) of the indented (Python) or braced (JS) block that starts at line i."""
    head = lines[i]
    ind = len(head) - len(head.lstrip())
    j = i + 1
    while j < len(lines):
        l = lines[j]
        if l.strip() and (len(l) - len(l.lstrip())) <= ind and not l.lstrip().startswith(("#", ")", "]", "}", "else", "elif", "except", "finally", "//")):
            break
        j += 1
    if j < len(lines) and lines[j].lstrip().startswith("}"):
        j += 1
    return i, min(j, i + 120)


def _loops(repo):
    out = []
    for rel in repo.files(CODE):
        text = repo.read(rel)
        if not LLM_SDK.search(text) and not LLM_CALL.search(text):
            continue
        lines = repo.lines(rel)
        for i, line in enumerate(lines):
            if _comment(line) or not LOOP.match(line):
                continue
            a, b = _block(lines, i)
            body = "\n".join(lines[a:b])
            if not LLM_CALL.search(body) and not (
                    re.search(r"processing_status|batches\.retrieve|\.status\b", line) and re.search(r"sleep\(", body)
                    and re.search(r"batch|llm|claude|anthropic|openai", text, re.I)):
                continue
            if BOUND.search(body) or INTERACTIVE.search(body):
                continue
            out.append(Hit(rel, i + 1, snippet(line),
                           "loop around an LLM call/batch poll with no iteration, deadline or budget bound"))
    return out


# ---------------------------------------------------------------- (3) HTTP to LLM without timeout
HTTP_LLM = re.compile(r"\b(?:requests|httpx|session|client)\.(?:post|request)\(|urllib\.request\.urlopen\(|\bfetch\(|"
                      r"\baxios\.post\(|\burlopen\(")
LLM_URL = re.compile(r"api\.anthropic\.com|api\.openai\.com|/chat/completions|/v1/messages|openai\.azure\.com|"
                     r"generativelanguage\.googleapis\.com|api\.mistral\.ai|api\.groq\.com|:11434/api")
TIMEOUT = re.compile(r"timeout|signal\s*:|AbortSignal|AbortController|abort\(|deadline", re.I)


def _http(repo):
    out = []
    for rel in repo.files(CODE):
        text = repo.read(rel)
        if not LLM_URL.search(text):
            continue
        lines = repo.lines(rel)
        for i, line in enumerate(lines):
            if _comment(line) or not HTTP_LLM.search(line):
                continue
            win = "\n".join(lines[max(0, i - 3): i + 14])
            if not LLM_URL.search("\n".join(lines[max(0, i - 8): i + 8])):
                continue
            if "timeout" in text.lower() and re.search(r"\bclient\s*=.*timeout|Timeout\(", text):  # client-level timeout
                continue
            if TIMEOUT.search(win):
                continue
            out.append(Hit(rel, i + 1, snippet(line), "HTTP call to an LLM API without a timeout (requests/fetch wait forever)"))
    return out


# ---------------------------------------------------------------- (4) endpoints
ROUTE = re.compile(r"""@\w+(?:\.\w+)*\.(?:post|put|patch)\(|@\w+(?:\.\w+)*\.route\([^)]*methods\s*=\s*[\[(][^\])]*["']POST|"""
                   r"""@\w+(?:\.\w+)*\.(?:api_route|websocket)\(""", re.I)
JS_ROUTE = re.compile(r"""\b(?:app|router|server)\.(?:post|put|patch)\(\s*["'`/]|export\s+(?:async\s+)?function\s+POST\b|"""
                      r"""export\s+const\s+POST\b""")
UI = re.compile(r"\bst\.(?:file_uploader|chat_input|text_area|button)\(|\bgr\.(?:Interface|Blocks)\(|\.launch\(")
RATE = re.compile(r"slowapi|\bLimiter\(|@\w*limiter\b|limiter\.limit|flask[_-]limiter|fastapi-limiter|express-rate-limit|"
                  r"django[_-]ratelimit|upstash/ratelimit|@\w*rate_?limit|(?i:rate_?limit(?:er|ing)?)\s*\(|RateLimit(?:er|Middleware)\b|"
                  r"throttle_classes|status_code\s*=\s*429|status\s*:\s*429|HTTP_429|(?i:too many requests)|"
                  r"\bburst\b\s*=|st\.session_state\[[\"']\w*(?:count|calls|requests)")
CAP = re.compile(r"max_length|maxLength|max_items|MAX_\w*(?:SIZE|BYTES|LEN\w*|CHARS|UPLOAD|FILE\w*|INPUT|PAGES|ROWS)\w*|"
                 r"content[-_]length|MAX_CONTENT_LENGTH|len\([^)]*\)\s*(?:>|>=)\s*\w+|\.size\s*(?:>|>=)|"
                 r"\.length\s*(?:>|>=)\s*\w+|\[\s*:\s*(?:\d+|[A-Z_]{4,})\s*\]|\.slice\(\s*0\s*,|\.substring\(\s*0\s*,|"
                 r"limit\s*:\s*[\"'`]\d|bodyParser\.\w+\([^)]*limit|express\.json\([^)]*limit|\.truncate|"
                 r"\.read\(\s*(?:\d|[A-Z_]{3})|MaxLen|constr\(|conlist\(|Field\([^)]*(?:max_|le=)|\b413\b|(?i:too large|too long|exceeds)")
LLM_PRICEY = re.compile(r"\.messages\.(?:create|stream)\(|\.chat\.completions\.|\.responses\.create\(|"
                        r"generate_content|generateContent|\.invoke\(|api\.anthropic\.com|api\.openai\.com|"
                        r"generateText|streamText|\.completions\.create\(")
CALLNAME = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


def _repo_has_rate_limit(repo):
    for rel in repo.files(CODE | {".json", ".toml", ".yaml", ".yml", ".txt", ".conf"}):
        if rel.endswith((".json", ".toml", ".yaml", ".yml", ".txt")) and not re.search(r"requirements|package\.json|pyproject", rel):
            continue
        if RATE.search(repo.read(rel)):
            return True
    return False


def _exposed(repo, rel):
    """Streamlit/Gradio UIs are single-user by default; count them only when the file itself, or a launch/config file in
    the same directory or an ancestor directory, binds to all interfaces."""
    if "bind" not in repo._cache:
        repo._cache["bind"] = [r for r in repo.files(CODE | {".toml", ".sh", ".yml", ".yaml"},
                                                     names={"dockerfile", "procfile"})
                               if re.search(r"0\.0\.0\.0|server\.address|share\s*=\s*True", repo.read(r))]
    d = rel.rsplit("/", 1)[0] if "/" in rel else ""
    for r in repo._cache["bind"]:
        rd = r.rsplit("/", 1)[0] if "/" in r else ""
        if r == rel or rd == "" or d == rd or d.startswith(rd + "/"):
            return True
    return False


GENERIC = {"main", "run", "get", "post", "call", "send", "process", "create", "init", "handle", "execute", "start",
           "load", "save", "read", "write", "update", "delete", "build", "parse", "test", "setup", "close", "open"}
_DEF = re.compile(r"^(\s*)(?:async\s+def|def)\s+(\w+)")


def _py_funcs(repo, rel):
    """(lines, {name: (start, end)}); a function ends at the next def of equal or lower indent (robust against
    unindented triple-quoted prompt text inside the body)."""
    lines = repo.lines(rel)
    defs = [(i, len(m.group(1)), m.group(2)) for i, l in enumerate(lines) if (m := _DEF.match(l))]
    by_name = {}
    for k, (i, ind, name) in enumerate(defs):
        end = len(lines)
        for j, ind2, _ in defs[k + 1:]:
            if ind2 <= ind:
                end = j
                break
        by_name[name] = (i, end)
    return lines, by_name


def _local_llm(lines, by_name):
    names = {n for n, (a, b) in by_name.items() if LLM_PRICEY.search("\n".join(lines[a:b]))}
    for _ in range(3):
        for n, (a, b) in by_name.items():
            if n not in names and any(c in names for c in CALLNAME.findall("\n".join(lines[a + 1:b]))):
                names.add(n)
    return names


def _llm_function_names(repo):
    """Names of Python functions (repo-wide) whose body reaches an LLM call, transitively (name-based, 3 rounds)."""
    if "llmfn" in repo._cache:
        return repo._cache["llmfn"]
    info = {}
    names = set()
    for rel in repo.files({".py"}):
        text = repo.read(rel)
        if not (LLM_CALL.search(text) or LLM_SDK.search(text)):
            continue
        lines, by_name = _py_funcs(repo, rel)
        info[rel] = (lines, by_name)
        for n, (a, b) in by_name.items():
            if LLM_PRICEY.search("\n".join(lines[a:b])) and n not in GENERIC and not n.startswith("test"):
                names.add(n)
    for _ in range(3):
        for rel, (lines, by_name) in info.items():
            for n, (a, b) in by_name.items():
                if n not in names and n not in GENERIC and any(
                        c in names for c in CALLNAME.findall("\n".join(lines[a + 1:b]))):
                    names.add(n)
    repo._cache["llmfn"] = names
    return names


JS_DECL = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)|^\s*(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*(?::\s*[\w<>\[\]| ]+)?\s*=>|\w+\s*=>)")


def _js_llm_names(repo):
    if "jsllm" in repo._cache:
        return repo._cache["jsllm"]
    decls = []
    names = set()
    for rel in repo.files({".js", ".ts", ".tsx", ".mjs", ".cjs", ".jsx"}):
        text = repo.read(rel)
        if not (LLM_PRICEY.search(text) or LLM_SDK.search(text)):
            continue
        lines = repo.lines(rel)
        for i, l in enumerate(lines):
            m = JS_DECL.match(l)
            if m:
                n = m.group(1) or m.group(2)
                a, b = _block(lines, i)
                body = "\n".join(lines[a:b])
                decls.append((n, body))
                if n not in GENERIC and n not in ("POST", "GET") and LLM_PRICEY.search(body):
                    names.add(n)
    for _ in range(3):
        for n, body in decls:
            if n not in names and n not in GENERIC and n not in ("POST", "GET") and set(CALLNAME.findall(body)) & names:
                names.add(n)
    repo._cache["jsllm"] = names
    return names


def _endpoints(repo):
    out = []
    cands = []
    llm_names = _llm_function_names(repo)
    js_names = _js_llm_names(repo)
    for rel in repo.files(CODE):
        text = repo.read(rel)
        lines = repo.lines(rel)
        if rel.endswith(".py"):
            if not ROUTE.search(text) and not UI.search(text):
                continue
            lines, by_name = _py_funcs(repo, rel)
            local = _local_llm(lines, by_name)
            imported = set(re.findall(r"^\s*from\s+[\w.]+\s+import\s+(\([^)]*\)|[^\n]+)", text, re.M))
            imported = {w for g in imported for w in re.findall(r"\w+", g)} & llm_names
            reach = local | imported
            for n, (a, b) in by_name.items():
                deco = "\n".join(lines[max(0, a - 4):a + 1])
                if not ROUTE.search(deco):
                    continue
                body = "\n".join(lines[a:b])
                if LLM_PRICEY.search(body) or (set(CALLNAME.findall(body[body.index(chr(10)) + 1:] if chr(10) in body else "")) & reach):
                    cands.append((rel, a + 1, snippet(lines[a]), body))
            if (_exposed(repo, rel) and UI.search(text) and not any(c[0] == rel for c in cands)
                    and re.search(r"st\.file_uploader|st\.chat_input|st\.text_area", text)
                    and (LLM_PRICEY.search(text) or set(CALLNAME.findall(text)) & reach)):
                cands.append((rel, 1, "streamlit UI input feeds an LLM call", text))
        else:
            for i, line in enumerate(lines):
                if JS_ROUTE.search(line):
                    seg = "\n".join(lines[i:min(len(lines), i + 90)])
                    if LLM_PRICEY.search(seg) or set(CALLNAME.findall(seg)) & js_names:
                        cands.append((rel, i + 1, snippet(line), seg))
    if not cands or _repo_has_rate_limit(repo):
        return out
    for rel, ln, head, body in cands:
        file_text = repo.read(rel)
        if CAP.search(body) or (CAP.search(file_text) and re.search(r"BaseModel|z\.object|zod|Schema", file_text) and
                                re.search(r"max_length|maxLength|\.max\(|Field\([^)]*max|constr", file_text)):
            continue
        out.append(Hit(rel, ln, head, "endpoint/UI action reaches an LLM call; no rate limit in the repo and no input size cap"))
    return out


def run(repo):
    hits = []
    for fn in (_redos, _loops, _http, _endpoints):
        hits.extend(fn(repo))
    return hits
