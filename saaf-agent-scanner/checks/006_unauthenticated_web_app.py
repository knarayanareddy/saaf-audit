"""SAAF-006: a web app / UI that listens on all interfaces exposes state-changing or LLM/tool routes with no
authentication anywhere in the app.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, snippet

CHECK = {
    "id": "SAAF-006",
    "slug": "unauthenticated-network-exposed-app",
    "category": "missing-authentication",
    "severity": "Medium",
    "title": "Web application listens on all network interfaces and exposes state-changing or LLM routes without authentication",
    "intended": "A service that triggers LLM calls, tools or data changes is reachable only by authenticated, authorised "
                "users (or is bound to localhost for single-user local use).",
    "actual": "The app binds to all interfaces (host 0.0.0.0, a public share link or a container/start command doing so) "
              "and defines POST/PUT/DELETE routes (or interactive UI actions) while no login, API key/token check, "
              "basic auth, session check or auth middleware exists in the app code.",
    "impact": "Anyone on the same network (or on the Internet when deployed) can call the endpoints directly: spend the "
              "LLM API quota, upload documents, trigger tool/agent runs and read, modify or delete the application's "
              "data and audit evidence, without any attribution.",
    "recommendation": "Bind to 127.0.0.1 unless remote access is required; add authentication to every state-changing "
                      "route (framework dependency/middleware, e.g. API key or OIDC/SSO, @login_required, Depends(auth), "
                      "gradio launch(auth=...), Streamlit login); put the app behind an authenticating reverse proxy; "
                      "add rate limits and request size limits for LLM routes.",
    "refs": "CWE-306, CWE-1327, OWASP LLM06, OWASP LLM10",
}

SRC_EXT = {".py", ".js", ".ts", ".mjs", ".cjs", ".sh", ".toml", ".yml", ".yaml"}
BIND_NAMES = {"dockerfile", "procfile", "package.json"}
BIND = [
    (re.compile(r"""\bhost\s*=\s*["'](0\.0\.0\.0|::)["']"""), "host=0.0.0.0"),
    (re.compile(r"""\bserver_name\s*=\s*["']0\.0\.0\.0["']"""), "gradio server_name=0.0.0.0"),
    (re.compile(r"""\.launch\([^)]*\bshare\s*=\s*True"""), "gradio share=True (public link)"),
    (re.compile(r"""--host["',\s=]+(0\.0\.0\.0|::)\b"""), "--host 0.0.0.0"),
    (re.compile(r"""--server\.address["',\s=]+0\.0\.0\.0"""), "streamlit server.address=0.0.0.0"),
    (re.compile(r"""^\s*address\s*=\s*["']0\.0\.0\.0["']"""), "streamlit address=0.0.0.0"),
    (re.compile(r"""\b(?:app|server)\.listen\(\s*[\w.]+\s*(?:\)|,\s*(?:\(|async\b|function\b))"""),
     "listen() without host (all interfaces)"),
    (re.compile(r"""\.listen\(\s*[\w.]+\s*,\s*["'](0\.0\.0\.0|::)["']"""), "listen(port, '0.0.0.0')"),
]
ROUTE_STATE = [
    re.compile(r"""@\w+(?:\.\w+)*\.(?:post|put|delete|patch)\(""", re.I),
    re.compile(r"""@\w+(?:\.\w+)*\.route\([^)]*methods\s*=\s*[\[(][^\])]*["'](?:POST|PUT|DELETE|PATCH)""", re.I),
    re.compile(r"""\b(?:app|router|server)\.(?:post|put|delete|patch)\(\s*["'`/]"""),
    re.compile(r"""^\s*@csrf_exempt\b"""),
]
UI_ACTION = re.compile(r"""\bst\.(?:button|chat_input|file_uploader|form_submit_button|data_editor)\(|"""
                       r"""\.(?:click|submit)\(\s*(?:fn\s*=|\w+\s*,\s*(?:inputs|outputs))|\bgr\.Interface\(""")
AUTH = re.compile(
    r"login_required|@\w*(?:auth|permission|requires?_)\w*|Depends\(\s*[\w.]*(?:auth|token|user|api_?key|verify|"
    r"secur|login|admin|permission|require|bearer|basic)|\bSecurity\(|HTTPBearer|HTTPBasic|APIKey(?:Header|Query|Cookie)|"
    r"OAuth2\w*|flask_login|flask_httpauth|flask_jwt|flask_security|LoginManager|HTTPBasicAuth|before_request|"
    r"@\w+\.middleware\(|add_middleware\((?!\s*(?:CORSMiddleware|GZip|TrustedHost))|BaseHTTPMiddleware|"
    r"(?:compare_digest|check_password_hash|verify_password|check_password)\(|"
    r"headers(?:\.get\(|\[)\s*[\"'](?:authorization|x-api-key|x-auth|api-key)|request\.authorization|"
    r"Header\([^)]*(?:authorization|api[-_]?key|token)|\.launch\([^)]*\bauth\s*=|streamlit_authenticator|"
    r"\bst\.login\b|\bst\.user\b|experimental_user|passport|express-session|express-basic-auth|req\.session|"
    r"jsonwebtoken|jwt\.verify|jwt\.decode|requireAuth|isAuthenticated|authMiddleware|next-auth|getServerSession|"
    r"AuthenticationMiddleware|LoginRequiredMixin|permission_classes|IsAuthenticated|"
    r"(?:getenv|environ(?:\.get)?|environ\[)\(?\s*[\"'](?!ANTHROPIC|OPENAI|GITHUB|HF_|HUGGING|LLM|AZURE|GOOGLE|GEMINI)"
    r"\w*(?:TOKEN|AUTH|PASSWORD|BEARER)\w*[\"']|process\.env\.(?!ANTHROPIC|OPENAI|GITHUB|HF_)\w*(?:TOKEN|AUTH|PASSWORD)\w*|"
    r"basic_?auth|session\.get\(\s*[\"'](?:user|logged|auth)|session\[[\"'](?:user|logged|auth)",
    re.I)


def _scope_files(repo, prefix):
    for rel in repo.files({".py", ".js", ".ts", ".mjs", ".cjs", ".toml", ".sh", ".tsx", ".jsx"}):
        if prefix == "" or rel.startswith(prefix + "/"):
            yield rel


def _is_comment(line):
    s = line.lstrip()
    return s.startswith(("#", "//", "*", "/*", "\"\"\"", "'''"))


def run(repo):
    binds = []   # (rel, lineno, line, kind)
    for rel in repo.files(SRC_EXT, BIND_NAMES):
        text = repo.read(rel)
        if not re.search(r"0\.0\.0\.0|::|share|listen\(|address", text):
            continue
        for i, line in enumerate(repo.lines(rel)):
            if _is_comment(line) or len(line) > 400:
                continue
            for rx, kind in BIND:
                if rx.search(line):
                    binds.append((rel, i, line, kind))
                    break
    if not binds:
        return []

    cache = {}

    def analyse(prefix):
        if prefix in cache:
            return cache[prefix]
        routes, auth = [], False
        for rel in _scope_files(repo, prefix):
            text = repo.read(rel)
            if AUTH.search(text):
                auth = True
                break
            for i, line in enumerate(repo.lines(rel)):
                if len(line) > 400 or _is_comment(line):
                    continue
                if any(rx.search(line) for rx in ROUTE_STATE) or UI_ACTION.search(line):
                    routes.append((rel, i, line))
        cache[prefix] = (routes, auth)
        return cache[prefix]

    hits, done = [], set()
    for rel, i, line, kind in binds:
        prefix = rel.rsplit("/", 1)[0] if "/" in rel else ""
        if prefix in done:
            continue
        routes, auth = analyse(prefix)
        if auth or not routes:
            continue
        done.add(prefix)
        hits.append(Hit(rel, i + 1, snippet(line),
                        f"binds all interfaces ({kind}); {len(routes)} state-changing route(s)/UI action(s) and no "
                        f"authentication marker under '{prefix or '.'}'; e.g. {routes[0][0]}:{routes[0][1] + 1} "
                        f"{snippet(routes[0][2], 80)}"))
    return hits
