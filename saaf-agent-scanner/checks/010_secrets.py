"""SAAF-010: real-format credentials (LLM provider keys, cloud keys, tokens, private keys, high-entropy password/api_key
assignments) committed to the working tree or, with --history, anywhere in git history including deleted files.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import math
import re
from _lib import Hit, snippet, redact

CHECK = {
    "id": "SAAF-010",
    "slug": "hardcoded-or-historic-secret",
    "category": "secret-in-git-history",
    "severity": "High",
    "title": "Real-format API key or credential is committed to the repository (working tree or git history)",
    "intended": "Credentials live only in environment variables or an untracked, git-ignored .env file; committed templates "
                "such as .env.example contain obvious placeholders.",
    "actual": "A string with the exact structure of a live credential (for example sk-ant-api03-<93 chars>, AKIA..., ghp_..., "
              "a PEM private key, or a high-entropy password/api_key value) is committed. Deleting the file in a later "
              "commit only removes it from the tip: the blob stays retrievable with `git log -p` / `git show <sha>:<path>` "
              "from every clone and fork.",
    "impact": "Anyone with read access to the repository, a fork or a CI cache can recover the secret and use it (model "
              "provider usage billed to the owner, access to the connected audit-data service, cloud access) until it is "
              "revoked. Liveness is not tested by the scanner; treat the key as compromised.",
    "recommendation": "Revoke and rotate the credential at the provider first (deleting the file does not revoke it); then "
                      "purge it from history (git filter-repo / BFG, force-push, ask forks to re-clone); keep real values in "
                      "an untracked .env listed in .gitignore, ship .env.example with placeholders only, and add a "
                      "pre-commit/CI secret scan (e.g. a secret scanner such as Gitleaks) over all refs.",
    "refs": "CWE-798, CWE-540, OWASP LLM02 (Sensitive Information Disclosure)",
}

# Provider formats: (kind, regex, min distinct chars)
FORMATS = [
    ("Anthropic API key", re.compile(r"sk-ant-(?:api\d{2}|admin\d{2})-[A-Za-z0-9_\-]{60,}"), 15),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-|svcacct-)[A-Za-z0-9_\-]{40,}|\bsk-(?!ant-)[A-Za-z0-9]{40,}"), 15),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 8),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{50,}"), 15),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), 15),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{20,}"), 10),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}"), 10),
]
PEM = re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----[ \t]*\r?\n"
                 r"(?:[+ \t]*[A-Za-z0-9+/=:,. \-]*\r?\n)?[+ \t]*[A-Za-z0-9+/=]{40,}")

NAME = r"(?:api[_-]?key|apikey|secret(?:[_-]?key)?|token|passw(?:or)?d|pwd|private[_-]?key|access[_-]?key|client[_-]?secret|auth[_-]?key)"
ASSIGN_QUOTED = re.compile(r"""(?i)["']?[\w.\-]*""" + NAME + r"""["']?\s*[:=]\s*[bfr]?["']([^"'\s]{12,})["']""")
ASSIGN_ENV = re.compile(r"""(?i)^\s*(?:export\s+)?[\w.\-]*""" + NAME + r"""\s*=\s*["']?([^"'\s]{12,})["']?\s*(?:\s#.*)?$""")

PLACEHOLDER = re.compile(
    r"x{3,}|\*{3,}|<[^>]*>|\.{3,}|your[_\-. ]|example|dummy|fake|sample|placeholder|changeme|change[_-]me|replace|redacted|"
    r"insert|generate|secret[_-]?here|key[_-]?here|token[_-]?here|todo|^test|test$|_test_|mock|0{6,}|1234|abcd|"
    r"^(none|null|true|false|undefined)$|password|^sk-?$|your-|my[_-]", re.I)
FORMAT_PLACEHOLDER = re.compile(r"x{4,}|\*{3,}|<[^>]*>|\.{3,}|example|dummy|fake|redacted|your[_\-]|placeholder|0{8,}|"
                                r"(?:abcd|1234){3,}", re.I)
ENV_NAMES = {".env", ".env.local", ".env.production", ".env.development", ".env.example", ".env.sample", ".env.template",
             ".env.dev", ".env.prod", ".env.staging", "env", ".envrc"}
SCAN_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".cfg",
            ".ini", ".env", ".sh", ".pem", ".key", ".properties", ".conf", ".ipynb", ".html", ".example", ".sample"}
CODE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
            ".sh", ".properties", ".conf")
SKIP_FILE = re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|Pipfile\.lock|"
                       r"composer\.lock|Cargo\.lock)$|\.min\.(js|css)$|\.map$", re.I)
TEST_DIR_RE = re.compile(r"(^|/)(tests?|testing|fixtures?|__tests__|spec|examples?)(/|$)", re.I)
DYNAMIC_VAL = re.compile(r"[${}()\[\]]|os\.|process\.env|getenv|environ|config|settings|\.get\b|^https?://|^[/.~]|"
                         r"^[A-Z][A-Z0-9_]+$|^[a-z][a-z0-9_]*$|^[a-z]+(?:[-_][a-z]+)+$|\\|^[\w.]+\.[\w.]+$")


def entropy(s):
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s)) if s else 0.0


def _classes(s):
    return sum(bool(re.search(p, s)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))


def _generic_ok(val):
    if len(val) < 12 or PLACEHOLDER.search(val) or DYNAMIC_VAL.search(val):
        return False
    return _classes(val) >= 3 and entropy(val) >= 3.0 and len(set(val)) >= 8


def find_secrets(line, is_env_file, code_like):
    """Yield (kind, secret_value) found on one line."""
    s = line.strip()
    if len(s) > 2000:
        return
    for kind, rx, mind in FORMATS:
        for m in rx.finditer(line):
            v = m.group(0)
            if FORMAT_PLACEHOLDER.search(v) or len(set(v)) < mind or v == "AKIAIOSFODNN7EXAMPLE":
                continue
            yield kind, v
    if s.startswith(("#", "//", "*", "<!--")) and not is_env_file:
        return
    if not (is_env_file or code_like):
        return
    m = ASSIGN_QUOTED.search(line) or (ASSIGN_ENV.search(line) if is_env_file else None)
    if m and _generic_ok(m.group(1)):
        yield "high-entropy credential assignment", m.group(1)


def _mask(v):
    return redact(v[:4] + "***")


def run(repo):
    hits, seen = [], set()

    def add(path, line, kind, val, detail):
        key = (path, val)
        if key in seen:
            return
        seen.add(key)
        hits.append(Hit(path, line, f"{kind}: {redact(_mask(val))}", detail))

    # 1. working tree (dotenv-style files are matched by name because Path('.env').suffix is empty)
    for rel in repo.files(SCAN_EXT, ENV_NAMES):
        low = rel.lower()
        base = low.rsplit("/", 1)[-1]
        if SKIP_FILE.search(rel):
            continue
        text = repo.read(rel)
        if not text or "\x00" in text[:1000]:
            continue
        is_env = base in ENV_NAMES or base.startswith(".env") or low.endswith((".env", ".properties"))
        code_like = low.endswith(CODE_EXT) and not low.endswith(".md")
        for i, line in enumerate(text.splitlines(), 1):
            for kind, val in find_secrets(line, is_env, code_like):
                add(rel, i, kind, val, "working tree")
        for m in PEM.finditer(text):
            add(rel, text.count("\n", 0, m.start()) + 1, "private key block", "-----BEGIN PRIVATE KEY", "working tree")

    # 2. git history (only with --history): added lines of every commit, incl. files deleted later
    patch = repo.git_log_patch()
    if patch:
        commit, path, deleted_later = "", "", set()
        buf = []
        for ln in patch.splitlines():
            if ln.startswith("@@COMMIT "):
                commit = ln[9:21]
            elif ln.startswith("+++ "):
                path = ln[6:] if ln.startswith("+++ b/") else ""
            elif ln.startswith("+") and path and not ln.startswith("+++"):
                if SKIP_FILE.search(path) or (not repo.include_tests and TEST_DIR_RE.search(path)):
                    continue
                low = path.lower()
                base = low.rsplit("/", 1)[-1]
                if not (base in ENV_NAMES or base.startswith(".env") or any(low.endswith(e) for e in SCAN_EXT)):
                    continue
                is_env = base in ENV_NAMES or base.startswith(".env") or low.endswith((".env", ".properties"))
                code_like = low.endswith(CODE_EXT)
                body = ln[1:]
                for kind, val in find_secrets(body, is_env, code_like):
                    # a value still present in the working tree is already reported above
                    if (path, val) in seen:
                        continue
                    still = val in repo.read(path) if (repo.root / path).is_file() else False
                    if still:
                        continue
                    add(path, 0, kind, val, f"git history only (added in commit {commit}; not in current tree)")
                if "PRIVATE KEY-----" in body and re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", body):
                    buf = [path, commit]
                elif buf and buf[0] == path and re.fullmatch(r"[A-Za-z0-9+/=]{40,}", body.strip()):
                    add(path, 0, "private key block", "-----BEGIN PRIVATE KEY", f"git history (commit {buf[1]})")
                    buf = []
                else:
                    buf = []
    return hits
