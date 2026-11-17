"""SAAF-012: an LLM agent is given unrestricted tools or runs without human approval (excessive agency).
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import json
import re
from _lib import Hit, functions, snippet

CHECK = {
    "id": "SAAF-012",
    "slug": "agent-excessive-permissions",
    "category": "excessive-agency-tool-permissions",
    "severity": "High",
    "title": "LLM agent runs with unrestricted tools or without human approval (bypassPermissions, Bash/Write, shell/REPL tools)",
    "intended": "The agent only has the minimum tools it needs (for example read-only tools), dangerous actions need human "
                "approval, and content from untrusted sources cannot reach a shell or file-writing tool.",
    "actual": "The agent is configured with permission_mode=\"bypassPermissions\"/\"acceptEdits\", --dangerously-skip-permissions, "
              "a wildcard allow rule such as Bash(*), an agent definition with Bash/Write that processes untrusted content, "
              "a shell or Python REPL tool (LangChain ShellTool/PythonREPLTool, CrewAI allow_code_execution=True), or a tool "
              "function that passes model-supplied arguments to subprocess. Note that allowed_tools=[] does NOT disable "
              "tools in the Claude Agent SDK; it only means nothing is pre-approved, and bypassPermissions then approves everything.",
    "impact": "Prompt injection in any document, repository, issue or web page the agent reads can make it run shell "
              "commands, read or overwrite files and exfiltrate data with the privileges of the host user, with no human "
              "in the loop (agent hijacking / remote code execution on the operator's workstation or server).",
    "recommendation": "For text-only LLM calls disable tools explicitly (tools=[] / disallowed_tools for every built-in tool) and "
                      "use permission_mode=\"default\" with a can_use_tool/approval callback. Grant read-only tools "
                      "(Read, Grep, Glob) to agents that read untrusted content; remove Bash/Write or scope them with "
                      "narrow rules such as Bash(git diff:*) plus deny rules; run code execution only in a sandbox "
                      "(container without network or secrets). Never pass model output to subprocess with shell=True; "
                      "validate against an allow-list and use argument lists.",
    "refs": "CWE-250, CWE-78, CWE-269, OWASP LLM06 (Excessive Agency)",
}

CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
SCRIPT_EXT = CODE_EXT | {".sh", ".yml", ".yaml", ".json", ".toml", ".cfg", ".service"}

COMMENT = re.compile(r"^\s*(#|//|\*|/\*|<!--)")
NEGATED = re.compile(r"\bnot\s+in\b|!=|\bassert\b|\bnot\b.*dangerously|forbid|prohibit|never\b|\bdeny\b|disallow|"
                     r"blocklist|denylist|\bbanned\b|\bre\.(compile|search|match)\b", re.I)

PERM_MODE = re.compile(r"""permission[_]?mode["']?\s*[:=]\s*["'](bypassPermissions|acceptEdits)["']|"""
                       r"""["']--permission-mode["']\s*,\s*["'](bypassPermissions|acceptEdits)["']|"""
                       r"""--permission-mode[ =](bypassPermissions|acceptEdits)|"""
                       r"""["']defaultMode["']\s*:\s*["'](bypassPermissions|acceptEdits)["']""", re.I)
SKIP_PERMS = re.compile(r"--dangerously-skip-permissions|allow[-_]dangerously[-_]skip[-_]permissions\s*[=:]\s*(True|true)|"
                        r"dangerously_skip_permissions\s*=\s*True")
EMPTY_ALLOWED = re.compile(r"allowed_?[tT]ools\s*[:=]\s*\[\s*\]")

RISKY_TOOL = re.compile(r"\b(ShellTool|PythonREPLTool|PythonAstREPLTool|BashProcess|LocalCommandLineCodeExecutor|"
                        r"ShellToolkit|TerminalTool)\b|allow_dangerous_code\s*=\s*True|allow_code_execution\s*=\s*True|"
                        r"""code_execution_mode\s*=\s*["']unsafe["']|use_docker\s*=\s*False|"""
                        r"""load_tools\(\s*\[[^\]]*["'](terminal|python_repl)["']""")
IMPORT_LINE = re.compile(r"^\s*(from|import)\s")

BAD_ALLOW_STRICT = re.compile(r"^(Bash|Write|Edit|MultiEdit|\*)(\(\s*(\*{1,2}|:\*|\*:\*)?\s*\))?$|^Bash\((\*{1,2}|:\*|\*:\*)\)$")

TOOL_DECOR = re.compile(r"^\s*@(\w+\.)*(tool|function_tool|kernel_function|mcp_tool|agent_tool|register_tool)\b|"
                        r"^\s*@\w+\.(tool|call_tool)\b")
SUBPROC = re.compile(r"\b(subprocess\.(run|Popen|call|check_output|check_call)|os\.system|os\.popen|"
                     r"asyncio\.create_subprocess_(shell|exec))\s*\(")
SUBPROC_GUARD = re.compile(r"allow[-_]?list|allowed_|ALLOWED|whitelist|WHITELIST|shlex\.quote|SAFE_|\bin\s+\(?[A-Z_]{4,}\b|"
                           r"\bin\s*[\(\{\[]\s*[\"']|startswith\(|fullmatch\(|human|approv|confirm", re.I)

UNTRUSTED_HINT = re.compile(r"untrusted|clone[sd]?\b|auditee|third[- ]party|user[- ]provided|uploaded|external (content|input|source|file)|"
                            r"issue body|pull request|web ?page|fetch(es|ing)?\b.*\burl|scrape|read(s|ing)? .*(repos?|repositor|documents?|emails?)|"
                            r"review(s|ing)? .*(repos?|repositor|code)|attacker|prompt injection", re.I)

AGENT_MD = re.compile(r"(^|/)(\.claude/agents|agents)/[^/]+\.md$", re.I)


def _frontmatter(text):
    if not text.startswith("---"):
        return None, ""
    m = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)", text, re.S)
    return (m.group(1), m.group(2)) if m else (None, "")


def _scan_lines(repo, rel, hits):
    lines = repo.lines(rel)
    ext = "." + rel.rsplit(".", 1)[-1].lower() if "." in rel.rsplit("/", 1)[-1] else ""
    is_code = ext in CODE_EXT
    text = "\n".join(lines)
    quick = ("ermission" not in text and "dangerously" not in text and "ShellTool" not in text and
             "REPL" not in text and "code_execution" not in text and "dangerous_code" not in text and
             "CommandLine" not in text and "use_docker" not in text and "load_tools" not in text and
             "BashProcess" not in text and "TerminalTool" not in text)
    if quick:
        return
    for i, line in enumerate(lines):
        if COMMENT.match(line):
            continue
        m = PERM_MODE.search(line)
        if m and not NEGATED.search(line):
            mode = next(g for g in m.groups() if g)
            near = "\n".join(lines[max(0, i - 8): i + 8])
            extra = " with allowed_tools=[] (does not disable tools)" if EMPTY_ALLOWED.search(near) else ""
            hits.append(Hit(rel, i + 1, snippet(line),
                            (f"permission mode {mode} auto-approves every tool call incl. Bash/Write/Edit{extra}" if mode.lower() == "bypasspermissions"
                             else f"permission mode {mode} auto-approves file edits without human review (Bash may still prompt; verify tool scope)")))
            continue
        if SKIP_PERMS.search(line) and not NEGATED.search(line) and (is_code or ext in SCRIPT_EXT):
            if not re.search(r"""["'](?:[^"']*\bnot\b[^"']*)["']""", line):
                hits.append(Hit(rel, i + 1, snippet(line), "agent CLI/SDK started with permission prompts disabled"))
                continue
        if is_code and RISKY_TOOL.search(line) and not IMPORT_LINE.match(line) and not NEGATED.search(line):
            hits.append(Hit(rel, i + 1, snippet(line), "shell / Python REPL / unsandboxed code-execution tool given to an agent"))


def _scan_settings(repo, rel, hits):
    text = repo.read(rel)
    try:
        data = json.loads(text)
    except ValueError:
        return
    if not isinstance(data, dict):
        return
    perms = data.get("permissions") if isinstance(data.get("permissions"), dict) else {}
    allow = perms.get("allow") if isinstance(perms.get("allow"), list) else []
    for rule in allow:
        if isinstance(rule, str) and BAD_ALLOW_STRICT.match(rule.strip()):
            ln = next((i + 1 for i, l in enumerate(repo.lines(rel)) if rule in l), 1)
            hits.append(Hit(rel, ln, snippet(f'"allow": "{rule}"'), "wildcard allow rule pre-approves unrestricted tool use"))
    if perms.get("defaultMode") in ("bypassPermissions", "acceptEdits"):
        ln = next((i + 1 for i, l in enumerate(repo.lines(rel)) if "defaultMode" in l), 1)
        hits.append(Hit(rel, ln, snippet(f'defaultMode: {perms["defaultMode"]}'), "default permission mode disables approval"))


def _scan_agent_md(repo, rel, hits):
    fm, body = _frontmatter(repo.read(rel))
    if not fm:
        return
    tm = re.search(r"^tools:\s*(.+)$", fm, re.M)
    if not tm:
        return
    tools = {t.strip(" []'\"") for t in re.split(r"[,\s]+", tm.group(1)) if t.strip(" []'\"")}
    risky = sorted(t for t in tools if re.match(r"^(Bash|Write|Edit|MultiEdit)\b", t) and not re.search(r"\(.+\)", t))
    if not risky or "Bash" not in " ".join(risky):
        return
    if not UNTRUSTED_HINT.search(body):
        return
    ln = fm[:tm.start()].count("\n") + 2
    hits.append(Hit(rel, ln, snippet(tm.group(0)),
                    f"agent definition grants {'/'.join(risky)} unscoped and its instructions process untrusted content"))


def _scan_tool_funcs(repo, rel, hits):
    text = repo.read(rel)
    if "subprocess" not in text and "os.system" not in text and "os.popen" not in text and "create_subprocess" not in text:
        return
    if not re.search(r"@\w*\.?(tool|function_tool|kernel_function|call_tool|register_tool|agent_tool)\b", text):
        return
    lines = repo.lines(rel)
    for a, b, head in functions(lines):
        # decorator directly above def
        k = a - 1
        decor = False
        while k >= 0 and lines[k].lstrip().startswith("@"):
            if TOOL_DECOR.match(lines[k]):
                decor = True
            k -= 1
        if not decor:
            continue
        body = lines[a:b]
        sig = re.match(r"\s*(?:async\s+)?def\s+\w+\s*\((.*?)\)\s*(->.*)?:", " ".join(l.strip() for l in lines[a:a + 6]))
        params = []
        if sig:
            for p in sig.group(1).split(","):
                n = re.match(r"\s*\*{0,2}(\w+)", p)
                if n and n.group(1) not in ("self", "cls", "ctx", "context"):
                    params.append(n.group(1))
        if not params or SUBPROC_GUARD.search("\n".join(body[1:])):
            continue
        for j in range(1, len(body)):
            if SUBPROC.search(body[j]):
                stmt = " ".join(x.strip() for x in body[j:j + 6])
                stmt = stmt.split(")\n")[0]
                shell = re.search(r"shell\s*=\s*True|os\.system|os\.popen|create_subprocess_shell", stmt)
                used = [p for p in params if re.search(r"\b" + re.escape(p) + r"\b", stmt)]
                if used and (shell or re.search(r"\[\s*" + re.escape(used[0]) + r"\b|\*\s*" + re.escape(used[0]) + r"\b|"
                                                 + re.escape(used[0]) + r"\.split\(|shlex\.split\(\s*" + re.escape(used[0]), stmt)
                            or re.search(r"\(\s*" + re.escape(used[0]) + r"\s*[,)]", stmt)):
                    hits.append(Hit(rel, a + j + 1, snippet(body[j]),
                                    f"tool function {head[:50]} passes model-supplied argument '{used[0]}' to a process without an allow-list"))
                    break


def run(repo):
    hits = []
    for rel in repo.files(SCRIPT_EXT):
        _scan_lines(repo, rel, hits)
    for rel in repo.files(CODE_EXT):
        _scan_tool_funcs(repo, rel, hits)
    for rel in repo.files({".json"}):
        low = rel.lower()
        if "/.claude/" in "/" + low and low.rsplit("/", 1)[-1].startswith("settings"):
            _scan_settings(repo, rel, hits)
    for rel in repo.files({".md"}):
        if AGENT_MD.search(rel):
            _scan_agent_md(repo, rel, hits)
    return hits
