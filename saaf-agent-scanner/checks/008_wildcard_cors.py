"""SAAF-008: CORS configured to accept any origin (allow_origins=["*"], flask_cors CORS(app) defaults, cors() with no
options, origin: true, Access-Control-Allow-
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, snippet

CHECK = {
    "id": "SAAF-008",
    "slug": "wildcard-cors",
    "category": "insecure-configuration",
    "severity": "Medium",
    "title": "CORS policy accepts requests from any origin (wildcard) on the application API",
    "intended": "Only the application's own frontend origin(s) may read responses from the API in a browser; a local or "
                "internal API is not reachable by arbitrary websites.",
    "actual": "The CORS layer allows every origin (allow_origins=[\"*\"], flask_cors CORS(app) with defaults, cors() without "
              "options, origin: true/'*', or an Access-Control-Allow-Origin: * header), often together with "
              "allow_methods/allow_headers=\"*\" and sometimes allow_credentials=True.",
    "impact": "Any web page the user visits can use the browser as a proxy to call the API (localhost or intranet) and "
              "read the responses. For agent backends that are unauthenticated or hold a GitHub/LLM token this lets a "
              "malicious site run the agent, read audit documents, change state and burn API quota; with credentials "
              "enabled, cookie or session-based auth is also exposed.",
    "recommendation": "Replace the wildcard with an explicit allow-list of the frontend origin(s) (read from configuration), "
                      "restrict allow_methods and allow_headers to what is needed, keep allow_credentials off unless "
                      "required, and require a token on every state-changing or data-returning endpoint instead of "
                      "relying on the network location. Do not reflect the request Origin header back.",
    "refs": "CWE-942, CWE-346, OWASP LLM06",
}

EXTS = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json", ".yml", ".yaml", ".toml", ".conf"}
STAR = r"[\"']\*[\"']"
# 1. Python / Starlette / FastAPI
CORSMW = re.compile(r"\bCORSMiddleware\b")
ALLOW_ORIGINS = re.compile(r"\ballow_origins\s*=\s*([^\n]*)")
ALLOW_REGEX = re.compile(r"\ballow_origin_regex\s*=\s*r?[\"']\.\*[\"']")
CREDS_PY = re.compile(r"\ballow_credentials\s*=\s*True")
# 2. flask_cors
FLASK_CORS_IMPORT = re.compile(r"\bflask_cors\b")
FLASK_CORS_CALL = re.compile(r"(?<![\w.])(?:CORS|cross_origin)\(")
# 3. literal header (python, js, nginx/apache style, next.config/vercel.json)
HEADER = re.compile(r"[\"']?Access-Control-Allow-Origin[\"']?\s*(?:[:,=]|\s)\s*[\"']?\*(?![\w/.-])|"
                    r"Access-Control-Allow-Origin[\"']\s*,\s*value\s*:\s*[\"']\*|"
                    r"\"key\"\s*:\s*\"Access-Control-Allow-Origin\"\s*,\s*\"value\"\s*:\s*\"\*\"", re.I)
# 4. django-cors-headers
DJANGO = re.compile(r"^\s*CORS_(?:ALLOW_ALL_ORIGINS|ORIGIN_ALLOW_ALL)\s*=\s*True", re.M)
# 5. node cors package
NODE_CORS_IMPORT = re.compile(r"require\(\s*[\"'](?:@fastify/)?cors[\"']\s*\)|from\s+[\"'](?:@fastify/)?cors[\"']|"
                              r"@koa/cors|@hono/cors|hono/cors")
NODE_CORS_EMPTY = re.compile(r"(?<![\w.])cors\(\s*\)")
NODE_CORS_OPTS = re.compile(r"(?<![\w.])cors\(\s*\{([^}]{0,300})\}\s*\)|\.register\(\s*\w*[cC]ors\w*\s*,\s*\{([^}]{0,300})\}")
NODE_ORIGIN_ANY = re.compile(r"\borigin\s*:\s*(?:true\b|[\"']\*[\"'])")


def _call_args(text, start):
    """Text of the call whose '(' is the first one at/after start (balanced, max 600 chars)."""
    i = text.find("(", start)
    if i < 0:
        return ""
    depth, j = 0, i
    while j < min(len(text), i + 600):
        c = text[j]
        depth += c == "("
        depth -= c == ")"
        if depth == 0:
            return text[i:j + 1]
        j += 1
    return text[i:j]


def _in_string_or_comment(text, pos):
    ls = text.rfind("\n", 0, pos) + 1
    prefix = text[ls:pos]
    s = prefix.lstrip()
    if s.startswith(("#", "//", "*", "/*")):
        return True
    return prefix.count('"') % 2 == 1 or prefix.count("'") % 2 == 1


INTENTIONAL_DEMO = re.compile(r"(^|/)(bad|vulnerable|insecure|intentionally[-_]\w+)[-_]?\w*(/|$)|(^|/)demo/bad", re.I)


def run(repo):
    hits = []
    for rel in repo.files(EXTS):
        if INTENTIONAL_DEMO.search(rel):  # deliberately vulnerable demo apps are not findings
            continue
        text = repo.read(rel)
        if "ors" not in text and "Access-Control" not in text and "ORS" not in text:
            continue
        low = rel.lower()
        is_py = low.endswith(".py")
        is_js = low.endswith((".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"))
        seen = set()

        def add(pos, detail):
            ln = text.count("\n", 0, pos) + 1
            if ln in seen:
                return
            seen.add(ln)
            hits.append(Hit(rel, ln, snippet(text.splitlines()[ln - 1]), detail))

        if is_py:
            for m in CORSMW.finditer(text):
                if _in_string_or_comment(text, m.start()):
                    continue
                line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.start()) if "\n" in text[m.start():] else None]
                if re.match(r"\s*(from|import)\b", line):
                    continue
                call = text[m.start(): m.start() + 500]
                end = re.search(r"\n\s*\)|\n\n|\n\S", call)
                call = call[: end.start()] if end else call
                call = text[m.start(): m.start() + 500][: len(call) + 3]
                wild = False
                for ao in ALLOW_ORIGINS.finditer(call):
                    if re.search(STAR, ao.group(1).split("allow_")[0]):
                        wild = True
                        break
                if ALLOW_REGEX.search(call):
                    wild = True
                if wild:
                    creds = " with allow_credentials=True" if CREDS_PY.search(call) else ""
                    add(m.start(), f"CORSMiddleware allows any origin{creds}")
            if FLASK_CORS_IMPORT.search(text):
                for m in FLASK_CORS_CALL.finditer(text):
                    if _in_string_or_comment(text, m.start()):
                        continue
                    args = _call_args(text, m.start())
                    has_origins = re.search(r"\borigins\b|\bresources\b", args)
                    star = re.search(r"\borigins\b\W{1,6}\*|\borigins\s*=\s*[\[\"']*\*|\"origins\"\s*:\s*[\[\"']*\*", args)
                    if "cross_origin" in text[m.start():m.start() + 14] and not star and has_origins:
                        continue
                    if star or not has_origins:
                        creds = " with supports_credentials=True" if "supports_credentials=True" in args else ""
                        how = "explicit wildcard origins" if star else "default (all origins)"
                        add(m.start(), f"flask_cors {how}{creds}")
            for m in DJANGO.finditer(text):
                add(m.start(), "django-cors-headers allows all origins")
        if is_js and NODE_CORS_IMPORT.search(text):
            for m in NODE_CORS_EMPTY.finditer(text):
                if not _in_string_or_comment(text, m.start()):
                    add(m.start(), "cors() with no options allows every origin")
            for m in NODE_CORS_OPTS.finditer(text):
                opts = m.group(1) or m.group(2) or ""
                if NODE_ORIGIN_ANY.search(opts) and not _in_string_or_comment(text, m.start()):
                    add(m.start(), "cors({origin: true|'*'}) allows/reflects every origin")
        for m in HEADER.finditer(text):
            s = text[text.rfind("\n", 0, m.start()) + 1: m.start()].lstrip()
            if s.startswith(("#", "//", "*", "/*")):
                continue
            pre = text[text.rfind("\n", 0, m.start()) + 1: m.start()]
            if is_py and (pre.count('"') % 2 == 1 or pre.count("'") % 2 == 1):
                continue
            add(m.start(), "Access-Control-Allow-Origin: * response header")
    return hits
