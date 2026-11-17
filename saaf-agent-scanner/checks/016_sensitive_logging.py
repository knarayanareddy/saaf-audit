"""SAAF-016: full prompts, raw model responses, uploaded documents, evidence, secrets or the process environment are
written to logs / stdout / append-only audit files, or uploaded documents are spilled to never-deleted temp files.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, functions, snippet, redact

CHECK = {
    "id": "SAAF-016",
    "slug": "sensitive-data-logged",
    "category": "sensitive-data-exposure-logging",
    "severity": "Low",
    "title": "Full prompts, model responses, uploaded documents or secrets are written to logs, stdout or "
             "unprotected files",
    "intended": "Logs and audit trails record metadata only (ids, sizes, hashes, timings, verdicts); audit "
                "documents, personal data, prompts and credentials never leave the controlled data store.",
    "actual": "A logging call, print(), append-only audit/jsonl write or temp file receives the complete prompt, "
              "message list, raw model response, document text, evidence, API key or process environment, with no "
              "redaction and no deletion of the copy.",
    "impact": "Confidential audit evidence and personal data (and in the worst case credentials) are copied into log "
              "files, CI/console output, log aggregators and temp directories that have broader access and longer "
              "retention than the source data, and are not covered by the application's redaction or "
              "retention rules.",
    "recommendation": "Log only identifiers, lengths and hashes (for example len(raw) and a SHA-256 prefix); put "
                      "full prompts/responses behind an explicit debug flag that is off by default and passes "
                      "through the redaction helper; never print keys or os.environ; write audit files with "
                      "restrictive permissions (0600, outside the repository tree); delete temporary copies of "
                      "uploads in a finally block or use a TemporaryDirectory context manager.",
    "refs": "CWE-532, CWE-312, CWE-377, OWASP LLM02",
}

LOG_CALL = re.compile(r"(?<![\w.])(?:self\.)?_{0,2}(?:logger|logging|log|LOG|LOGGER|_log|_logger)\."
                      r"(?:debug|info|warning|warn|error|exception|critical)\s*\(")
PRINT_CALL = re.compile(r"(?<![\w.])print\s*\(")
STR_LIT = re.compile(r"""([rbuRBU]?[fF][rbRB]?|[rbuRBU]?)("{3}|'{3}|"|')((?:\\.|(?!\2).)*?)\2""", re.S)
WRAPPERS = re.compile(r"\b(?:len|redact\w*|mask\w*|scrub\w*|sanitize\w*|sanitise\w*|anonymi\w*|pseudonymi\w*|"
                      r"\w*(?:sha\d*|hash|digest|md5|fingerprint)\w*|bool|type|id|count\w*)\s*\(")
CHAIN = re.compile(r"[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*")

SENS = {"prompt", "prompts", "messages", "transcript", "evidence", "document", "documents", "upload", "uploaded"}
MSG_RESP = re.compile(r"response|output|reply|completion|llm|model|claude|gpt|prompt|answer", re.I)
SECRET = {"apikey", "secret", "secrets", "password", "passwd", "credentials", "bearer"}
SAFE = {"path", "paths", "file", "files", "filename", "name", "names", "len", "length", "count", "size", "hash",
        "sha", "sha256", "digest", "id", "ids", "version", "dir", "template", "time", "status", "code", "type",
        "model", "usage", "ms", "env", "var", "label", "title", "kind", "index", "idx", "num", "total", "mode",
        "exists", "found", "present", "set", "configured", "enabled", "keys", "key_id", "url", "uri", "ext",
        "format", "tokens", "n", "stats", "summary", "result", "results", "meta", "metadata", "error", "exc", "percent", "percentage", "pct", "rate", "score"}
RESP_CTX = {"text", "content", "body", "llm", "claude", "model", "full", "output", "completion"}
# `raw` alone is only meaningful for response-like data; these 'raw' contexts are benign
RAW_BENIGN = {"raw_len", "raw_path"}


def _strip_calls(s):
    """Remove len()/hash()/redact() style wrappers (with their arguments) so their arguments are not reported."""
    for _ in range(6):
        m = WRAPPERS.search(s)
        if not m:
            break
        i, depth = m.end(), 1
        while i < len(s) and depth:
            depth += {"(": 1, ")": -1}.get(s[i], 0)
            i += 1
        s = s[:m.start()] + " " + s[i:]
    return s


def _expr_of_args(text):
    """Code-only view of a call: plain string literals dropped, f-string {expressions} kept."""
    def lit(m):
        if "f" in m.group(1).lower():
            return " " + " ".join(re.findall(r"\{([^{}]*)\}", m.group(3))) + " "
        return " "
    return STR_LIT.sub(lit, text)


def _split(name):
    return [t for t in re.split(r"_+", re.sub(r"([a-z])([A-Z])", r"\1_\2", name).lower()) if t]


def sensitive_names(code, msg=""):
    """Return identifiers/chains in `code` that look like sensitive payloads (prompt/response/document/secret)."""
    found = []
    for m in CHAIN.finditer(_strip_calls(code)):
        chain = re.sub(r"\s+", "", m.group(0))
        parts = chain.split(".")
        if parts[0] in ("args", "opts", "options", "cli", "parser"):
            continue
        if parts[0] in ("self", "cls"):
            parts = parts[1:]
        if not parts:
            continue
        last = _split(parts[-1])
        if parts[-1].lower() in RAW_BENIGN or set(last) & SAFE:
            continue
        # method names like .get/.items/.join/.format are not payloads themselves
        if parts[-1] in ("get", "items", "keys", "values", "join", "format", "strip", "split", "lower", "upper",
                         "encode", "decode", "dumps", "loads", "read", "write"):
            continue
        toks = set(last)
        ctx = set(t for p in parts[:-1] for t in _split(p))
        joined = "".join(last)
        if "apikey" in joined or "api_key" in parts[-1].lower() or toks & SECRET or \
                (toks & {"token"} and toks & {"api", "access", "auth", "bearer", "secret", "refresh"}):
            found.append(chain)
        elif toks & {"raw"} and ((toks | ctx) & (RESP_CTX | {"response", "resp", "reply", "answer", "json"})
                                 or MSG_RESP.search(msg)):
            found.append(chain)          # raw model output (a bare `raw` needs the log message to say what it is)
        elif toks & {"response", "resp", "reply", "answer"} and toks & (RESP_CTX | {"raw"}):
            found.append(chain)
        elif toks & SENS:
            found.append(chain)
        elif toks & {"text", "content"} and ctx & {"response", "resp", "message", "document", "doc", "upload",
                                                    "uploaded", "pdf", "prompt"}:
            found.append(chain)
        elif toks & {"text", "content", "body"} and toks & {"doc", "document", "pdf", "user", "input",
                                                             "full", "source", "evidence", "uploaded"}:
            found.append(chain)
    return found


def _call_text(lines, i, start_col):
    """Return the text of the call starting at line i (paren-balanced, at most 8 lines)."""
    buf, depth, started = [], 0, False
    for j in range(i, min(i + 8, len(lines))):
        seg = lines[j][start_col:] if j == i else lines[j]
        buf.append(seg)
        for ch in seg:
            if ch == "(":
                depth += 1; started = True
            elif ch == ")":
                depth -= 1
        if started and depth <= 0:
            break
    return " ".join(buf)


ENV_DUMP = re.compile(r"(?<!in )(?<!in os\.)\benviron\b(?!\s*(?:\.get\s*\(|\[))|\bdict\(\s*(?:os\.)?environ|getenv\([^)]*(?:KEY|SECRET|TOKEN|PASSWORD)",
                      re.I)
APPEND_OPEN = re.compile(r"""open\s*\([^)]*["'](?:a|ab|a\+|at)["']|\.open\s*\(\s*["'](?:a|ab|a\+|at)["']""")
LOGISH_PATH = re.compile(r"log|audit|jsonl|history|trace|transcript", re.I)
WRITE_CALL = re.compile(r"\.write\s*\(|json\.dump\s*\(|\.writerow\s*\(")
TEMP_KEEP = re.compile(r"NamedTemporaryFile\s*\([^)]*delete\s*=\s*False|mkstemp\s*\(|mktemp\s*\(")
UPLOAD_SIGNS = re.compile(r"getbuffer\(|getvalue\(|file_uploader|UploadFile|request\.files|uploaded|\.save\s*\(", re.I)
CLEANUP = re.compile(r"os\.(?:unlink|remove)\s*\(|\.unlink\s*\(|shutil\.rmtree|TemporaryDirectory|atexit|rmtree")


def run(repo):
    hits = []
    for rel in repo.files({".py"}):
        text = repo.read(rel)
        lines = repo.lines(rel)
        seen = set()

        def add(i, detail, ev=None, plain=False):
            if i not in seen:
                seen.add(i)
                e = ev if ev is not None else snippet(lines[i])
                hits.append(Hit(rel, i + 1, e if plain else redact(e), detail))

        # A/B/C: logging calls, print(), environment dumps
        if re.search(r"log|print", text, re.I):
            for i, line in enumerate(lines):
                if line.lstrip().startswith("#"):
                    continue
                m = LOG_CALL.search(line)
                kind = "log call"
                if not m:
                    m = PRINT_CALL.search(line)
                    kind = "print()"
                if not m:
                    continue
                call = _call_text(lines, i, m.start())
                if kind == "print()" and re.search(r"file\s*=\s*(?!sys\.std(?:err|out))", call):
                    continue                     # print(..., file=handle) writes to a file; not stdout
                argtxt = call[m.end() - m.start():]
                code = _expr_of_args(argtxt)
                msg = " ".join(g[2] for g in STR_LIT.findall(argtxt))
                names = sensitive_names(code, msg)
                if names:
                    add(i, f"{kind} emits the value of {', '.join(sorted(set(names))[:3])}")
                elif ENV_DUMP.search(_strip_calls(code)):
                    add(i, f"{kind} emits the process environment or a secret environment variable")

        # D: append-only audit/jsonl files that receive full prompts/responses
        if APPEND_OPEN.search(text):
            for a, b, head in functions(lines):
                body = lines[a:b]
                if not any(APPEND_OPEN.search(l) and (LOGISH_PATH.search(l) or LOGISH_PATH.search(head) or
                                                      LOGISH_PATH.search(rel)) for l in body):
                    continue
                for k in range(a, b):
                    w = WRITE_CALL.search(lines[k])
                    if not w:
                        continue
                    names = sensitive_names(_expr_of_args(_call_text(lines, k, w.start())[w.end() - w.start():]))
                    if names:
                        add(k, f"audit/log file append receives the full value of {', '.join(sorted(set(names))[:3])}")

        # E: uploaded documents spilled to temp files that are never removed
        if TEMP_KEEP.search(text) and UPLOAD_SIGNS.search(text) and not CLEANUP.search(text):
            for i, line in enumerate(lines):
                if TEMP_KEEP.search(line):
                    add(i, "uploaded content appears to be written to a temp file that nothing in this module deletes",
                        plain=True)
                    break
    return hits
