"""SAAF-017: an OS command or SQL statement is assembled from variables with f-strings / format / % / concatenation
and executed through a shell or a SQL driver, instead of an argument vector or bound parameters.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import bisect
import re
from _lib import Hit, snippet

CHECK = {
    "id": "SAAF-017",
    "slug": "shell-or-sql-injection",
    "category": "injection-sql-cmd",
    "severity": "High",
    "title": "Shell command or SQL statement is built from variables by string interpolation (command / SQL injection)",
    "intended": "External programs are started with an argument vector (no shell) and SQL statements use bound "
                "parameters, so that data supplied by users, repositories, documents or the LLM can never change the "
                "structure of the command or query.",
    "actual": "A command string is built with an f-string, str.format, % formatting, concatenation or a JavaScript "
              "template literal and is run through a shell (subprocess with shell=True, os.system/os.popen, "
              "child_process.exec/execSync, `bash -c`, bash eval), or a SQL string built the same way is passed to "
              "execute()/query()/text()/raw(); the interpolated values are not escaped with shlex.quote or bound as "
              "parameters.",
    "impact": "Any value that reaches the interpolated variable (an unauthenticated form field, a file name inside an "
              "uploaded or cloned repository, a document field, an LLM tool argument) can inject shell metacharacters "
              "(; | $() backticks) or SQL syntax, giving command execution as the service or operator account, or "
              "reading and modifying the database.",
    "recommendation": "Pass commands as a list without a shell (subprocess.run([...]) / execFile / spawn without "
                      "shell:true) and put '--' before untrusted positional values; where a shell is unavoidable wrap "
                      "every value with shlex.quote (shell-quote in Node) after validating it against a strict "
                      "allowlist pattern. For SQL use bound parameters (cursor.execute(sql, params), `?`/`%s`/`$1` "
                      "placeholders, ORM query builders) and allowlist identifiers such as table or column names; in "
                      "bash never use eval on values taken from input, quote them and call the program directly.",
    "refs": "CWE-78, CWE-89, OWASP LLM05 (Improper Output Handling), OWASP A03:2021",
}

# ---- sinks --------------------------------------------------------------------------------------------------------
PY_SHELL_SINK = re.compile(
    r"\b(?:subprocess\.(?:run|call|check_call|check_output|Popen|getoutput|getstatusoutput)|Popen|check_output|"
    r"check_call|os\.system|os\.popen|commands\.getoutput|asyncio\.create_subprocess_shell|"
    r"(?:pexpect\.)?(?:spawn|run))\s*\(")
PY_SHELL_NAMES_NEEDING_FLAG = re.compile(r"^(?:subprocess\.(?:run|call|check_call|check_output|Popen)|Popen|check_output|"
                                         r"check_call|(?:pexpect\.)?(?:spawn|run))$")
PY_ALWAYS_SHELL = re.compile(r"os\.system|os\.popen|commands\.getoutput|getoutput|getstatusoutput|create_subprocess_shell")
SHELL_C = re.compile(r"[\"'](?:ba|z|da|k)?sh[\"']\s*,\s*[\"']-l?c[\"']\s*,")
PY_SQL_SINK = re.compile(r"(?<![\w])(?:\.\s*)?(?:execute|executemany|executescript|exec_driver_sql|read_sql|read_sql_query|"
                         r"read_sql_table|raw|text|RawSQL|mogrify)\s*\(")
JS_CP_SINK = re.compile(r"(?<![\w.$])(?:exec|execSync)\s*\(|\b(?:child_process|childProcess|cp|proc|shell|shelljs|sh)"
                        r"\.(?:exec|execSync)\s*\(")
JS_CP_FILE = re.compile(r"child_process|shelljs|\bexeca\b|node:child_process")
JS_SQL_SINK = re.compile(r"\.\s*(?:query|execute|run|all|get|exec|prepare|raw|\$queryRawUnsafe|\$executeRawUnsafe|"
                         r"unsafe|queryRawUnsafe)\s*\(")

SQL_KW = re.compile(r"\b(?:select\b[^\n]{0,200}?\bfrom|insert\s+(?:or\s+\w+\s+)?into|update\s+[\w.\"`\[\]{}$]+\s+set|"
                    r"delete\s+from|drop\s+(?:table|database|index|view)|alter\s+table|create\s+(?:table|index|view)|"
                    r"pragma\s+\w+|truncate\s+table|replace\s+into|where\s+[\w.`\"]+\s*(?:=|like|in|<|>))", re.I)

# ---- dynamic-string detection -------------------------------------------------------------------------------------
QUOTED = re.compile(r"(?:shlex\.)?quote\([^()]*\)|shlex\.join\([^()]*\)|shell-?quote\([^()]*\)|shellEscape\([^()]*\)|"
                    r"escapeShell\w*\([^()]*\)|\bint\([^()]*\)|\bfloat\([^()]*\)|\bnumber\([^()]*\)|\blen\([^()]*\)|"
                    r"parseInt\([^()]*\)|Number\([^()]*\)")
PY_FSTR = re.compile(r"""\b[rRbB]?[fF][rR]?(\"\"\"|'''|"|')(.*?)(?<!\\)\1""", re.S)
JS_TPL = re.compile(r"`((?:[^`\\]|\\.)*)`", re.S)
EXPR_PY = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")
EXPR_JS = re.compile(r"\$\{([^{}]+)\}")
# interpolations that are safe by nature: constants, placeholders, identifier lists, numbers
SAFE_EXPR = re.compile(
    r"^\s*(?:(?:\w+\.)*(?:placeholders?|qmarks?|marks|columns?|cols|fields?|table(?:_name)?|tbl|order_by|limit|offset)"
    r"|.*[\"']\?[\"']\s*\*.*|.*[\"']\?[\"']\s*\.?join.*|.*[\"']%s[\"']\s*\.?join.*|"
    r".*[\"'],\s*[\"']\s*\.?join.*\blen\(.*)\s*(?:!r|:[\w.,<>^=+-]*)?\s*$", re.I | re.S)
SAFE_EXPR_CS = re.compile(r"^\s*[A-Z][A-Z0-9_]*\s*$")


def _scrub(text):
    return QUOTED.sub("Q", text)


def _fstring_dyn(text, sql):
    for m in PY_FSTR.finditer(text):
        body = m.group(2)
        for e in EXPR_PY.finditer(body):
            ex = e.group(1).strip()
            if ex in ("Q", "{Q}") or SAFE_EXPR_CS.match(ex):
                continue
            if sql and SAFE_EXPR.match(ex):
                continue
            return True
    return False


def _tpl_dyn(text, sql):
    for m in JS_TPL.finditer(text):
        for e in EXPR_JS.finditer(m.group(1)):
            ex = e.group(1).strip()
            if ex in ("Q", "{Q}") or SAFE_EXPR_CS.match(ex):
                continue
            if sql and SAFE_EXPR.match(ex):
                continue
            return True
    return False


FORMAT_CALL = re.compile(r"[\"']\s*\.\s*format\s*\((?!\s*\))")
PCT_FMT = re.compile(r"[\"']\s*%\s*(?:\(|[A-Za-z_])")
CONCAT = re.compile(r"[\"'`]\s*\+\s*(?!Q\b)[A-Za-z_(\[]|(?<![\"'`\s])(?<!\bQ)[\w\])]\s*\+\s*[\"'`]")


def dynamic(text, lang, sql=False):
    """True when the (already extracted) argument text builds a string from variables."""
    t = _scrub(text)
    if lang == "py":
        if _fstring_dyn(t, sql):
            return True
        if FORMAT_CALL.search(t) or PCT_FMT.search(t):
            return not (sql and _only_safe_format(t))
    else:
        if _tpl_dyn(t, sql):
            return True
    return bool(CONCAT.search(t)) and not (sql and _only_safe_format(t))


def _only_safe_format(t):
    # `"... IN (%s)" % ",".join("?" * n)` style placeholder generation
    return bool(re.search(r"\?\s*\"?'?\s*\*|join\(\s*[\"']\?|%s[\"']\s*\*|placeholders?", t, re.I))


# ---- text helpers -------------------------------------------------------------------------------------------------
def call_args(text, start, limit=2500):
    """Return the text inside the balanced parentheses that open at index start-1 (quote-aware, crude)."""
    depth, i, n, q = 1, start, min(len(text), start + limit), None
    while i < n:
        c = text[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if text.startswith(q, i):
                i += len(q)
                q = None
                continue
        else:
            if text.startswith(('"""', "'''"), i):
                q = text[i:i + 3]
                i += 3
                continue
            if c in "\"'`":
                q = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
                if depth == 0:
                    return text[start:i]
        i += 1
    return text[start:n]


def first_arg(args):
    depth, q, i = 0, None, 0
    while i < len(args):
        c = args[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if args.startswith(q, i):
                i += len(q)
                q = None
                continue
        else:
            if args.startswith(('"""', "'''"), i):
                q = args[i:i + 3]
                i += 3
                continue
            if c in "\"'`":
                q = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == "," and depth == 0:
                return args[:i]
        i += 1
    return args


def lookback_assign(lines, idx, name, lang):
    """Nearest assignment to `name` above line idx inside the same function; returns the assigned text or ''."""
    rx = re.compile(r"^\s*(?:(?:const|let|var|final)\s+)?(?:self\.)?" + re.escape(name) + r"\s*(?::[^=\n]+)?\+?=(?!=)\s*")
    out = []
    for j in range(idx - 1, max(-1, idx - 80), -1):
        l = lines[j]
        if lang == "py" and re.match(r"\s*(?:async\s+)?def\s", l):
            break
        if rx.match(l):
            buf = [l[rx.match(l).end():]]
            k = j + 1
            while k < min(len(lines), j + 12) and k < idx and (_open(buf) or buf[-1].rstrip().endswith(("+", "\\", ","))):
                buf.append(lines[k])
                k += 1
            out.append("\n".join(buf))
    return "\n".join(out)


def _open(buf):
    t = "\n".join(buf)
    return (t.count("(") + t.count("[") + t.count("{") > t.count(")") + t.count("]") + t.count("}")
            or t.count('"""') % 2 == 1 or t.count("'''") % 2 == 1 or t.count("`") % 2 == 1)


IDENT = re.compile(r"^\s*(?:self\.)?([A-Za-z_]\w*)\s*$")


NUMERIC_SRC = re.compile(r"^\s*(?:await\s+)?(?:parseInt|parseFloat|Number|int|float|len|uuid\.uuid4|str\(\s*uuid)\b")
SIMPLE_INTERP = re.compile(r"(?:\$\{|(?<!\{)\{)\s*([A-Za-z_]\w*)\s*\}")


def _numeric_idents(arg, lines, line_idx, lang):
    """Replace `${id}` / `{id}` by Q when id was assigned from parseInt()/int()/Number() earlier in the function."""
    def sub(m):
        a = lookback_assign(lines, line_idx, m.group(1), lang)
        return "Q" if a and NUMERIC_SRC.match(a) else m.group(0)
    return SIMPLE_INTERP.sub(lambda m: ("${Q}" if lang == "js" else "{Q}") if sub(m) == "Q" else m.group(0), arg)


def arg_is_dynamic(arg, lines, line_idx, lang, sql):
    if "{" in arg:
        arg = _numeric_idents(arg, lines, line_idx, lang)
    if dynamic(arg, lang, sql):
        return True
    m = IDENT.match(arg)
    if m:
        assigned = lookback_assign(lines, line_idx, m.group(1), lang)
        if assigned and dynamic(assigned, lang, sql):
            return not sql or bool(SQL_KW.search(assigned))
    return False


# ---- per-language scanners ----------------------------------------------------------------------------------------
def line_offsets(text):
    offs, p = [0], 0
    for l in text.split("\n"):
        p += len(l) + 1
        offs.append(p)
    return offs


def scan_py(rel, text, lines):
    hits, offs, seen = [], line_offsets(text), set()
    for m in PY_SHELL_SINK.finditer(text):
        name = re.sub(r"\s*\($", "", m.group(0))
        ln = bisect.bisect_right(offs, m.start()) - 1
        if lines[ln].lstrip().startswith("#") or ln in seen:
            continue
        args = call_args(text, m.end())
        shell = bool(PY_ALWAYS_SHELL.search(name)) or bool(re.search(r"shell\s*=\s*True", args)) or bool(SHELL_C.search(args))
        if not shell:
            continue
        if name in ("run", "spawn", "pexpect.run", "pexpect.spawn") and not re.search(r"shell\s*=\s*True|pexpect", text):
            continue
        a1 = first_arg(args)
        if SHELL_C.search(args):   # ["bash", "-c", f"..."] -> the command string is the 3rd element
            a1 = args[SHELL_C.search(args).end():]
        if arg_is_dynamic(a1, lines, ln, "py", False):
            seen.add(ln)
            hits.append(Hit(rel, ln + 1, snippet(lines[ln]), "shell command string built from variables and run through a shell"))
    if re.search(r"execute|read_sql|text\(|raw\(|RawSQL|mogrify", text):
        for m in PY_SQL_SINK.finditer(text):
            ln = bisect.bisect_right(offs, m.start()) - 1
            if lines[ln].lstrip().startswith("#") or ln in seen:
                continue
            args = call_args(text, m.end())
            a1 = first_arg(args)
            if not (SQL_KW.search(a1) or IDENT.match(a1)):
                continue
            if m.group(0).lstrip(". ").startswith(("text", "raw")) and not SQL_KW.search(a1) and not IDENT.match(a1):
                continue
            if IDENT.match(a1) and not m.group(0).lstrip(". ").startswith(("execute", "read_sql", "exec_driver")):
                continue
            if arg_is_dynamic(a1, lines, ln, "py", True):
                seen.add(ln)
                hits.append(Hit(rel, ln + 1, snippet(lines[ln]), "SQL statement built from variables instead of bound parameters"))
    return hits


def scan_js(rel, text, lines):
    hits, offs, seen = [], line_offsets(text), set()
    if JS_CP_FILE.search(text):
        for m in JS_CP_SINK.finditer(text):
            ln = bisect.bisect_right(offs, m.start()) - 1
            if lines[ln].lstrip().startswith(("//", "*")) or ln in seen:
                continue
            a1 = first_arg(call_args(text, m.end()))
            if arg_is_dynamic(a1, lines, ln, "js", False):
                seen.add(ln)
                hits.append(Hit(rel, ln + 1, snippet(lines[ln]), "child_process.exec runs a command string built from variables through /bin/sh"))
    for m in JS_SQL_SINK.finditer(text):
        ln = bisect.bisect_right(offs, m.start()) - 1
        if lines[ln].lstrip().startswith(("//", "*")) or ln in seen:
            continue
        a1 = first_arg(call_args(text, m.end()))
        if SQL_KW.search(a1) and arg_is_dynamic(a1, lines, ln, "js", True):
            seen.add(ln)
            hits.append(Hit(rel, ln + 1, snippet(lines[ln]), "SQL statement built from variables instead of bound parameters"))
    return hits


SH_EVAL = re.compile(r"(?:^|[;&|(]\s*|\bthen\s+|\bdo\s+)(?:eval|(?:ba|z|da)?sh\s+-c)\s+(.*)$")
SH_VAR = re.compile(r"\$\{?[A-Za-z_][A-Za-z_0-9]*|\$[1-9@*]")


def scan_sh(rel, lines):
    hits = []
    for i, l in enumerate(lines):
        s = l.strip()
        if not s or s.startswith("#"):
            continue
        m = SH_EVAL.search(s)
        if not m or m.group(1).lstrip().startswith("'"):
            continue
        rest = re.sub(r"\$\((?:[^()]|\([^()]*\))*\)|`[^`]*`", "", m.group(1))   # ignore eval "$(tool init)"
        rest = re.sub(r"\$\{?\w+\}?\s*$", "", rest.strip().strip("\"'")) if re.fullmatch(r"[\"']?\$\{?[\w@*]+\}?[\"']?\s*;?", rest.strip()) else rest
        if SH_VAR.search(rest) and re.search(r"\w[^$]*\$|\$[^\s\"']+[^\s\"']*[A-Za-z0-9/._-]", rest) and not re.search(r"printf\s+%q|\$\{[^}]*@Q\}", rest):
            hits.append(Hit(rel, i + 1, snippet(l), "shell eval / sh -c interpolates a variable into the command text"))
    return hits


def run(repo):
    hits = []
    for rel in repo.files({".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".sh", ".bash"}):
        text = repo.read(rel)
        if not text:
            continue
        low = rel.lower()
        lines = text.split("\n")
        if low.endswith(".py"):
            if re.search(r"subprocess|os\.system|os\.popen|Popen|execute|read_sql|text\(|raw\(|getoutput|spawn|mogrify", text):
                hits += scan_py(rel, text, lines)
        elif low.endswith((".sh", ".bash")):
            if "eval" in text or "-c" in text:
                hits += scan_sh(rel, lines)
        else:
            if re.search(r"exec|query|execute|\.run\(|\.all\(|\.get\(|prepare|raw|unsafe", text):
                hits += scan_js(rel, text, lines)
    return hits
