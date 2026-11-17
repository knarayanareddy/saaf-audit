"""Deterministic static signals for drift drivers (D1-D5), controls (C1-C5), the agency
profile, and the six Drift Watch red flags.

Python files are parsed with ``ast`` where possible; a SyntaxError (e.g. 3.10+ ``match`` on a
3.9 interpreter) falls back to regex at lower confidence. JS/TS use regex only. Each signal
records a path, a 1-indexed line, the dimension, an implied 1-5 level and a confidence; no
code text leaves the run directory.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PY = ".py"
JSTS = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}


@dataclass
class Signal:
    dimension: str           # D1..D5, C1..C5, AG (agency)
    rule: str                # short machine id, e.g. "write_instruction_path"
    path: str
    line: int
    level: int               # implied 1-5 for the dimension
    confidence: str = "medium"  # high | medium | low
    note: str = ""
    mitigates: bool = False  # a control signal (raises control strength)


@dataclass
class UnitSignals:
    signals: List[Signal] = field(default_factory=list)
    agency: str = "advisory"            # advisory | assisted | autonomous
    action_capable: bool = False
    syntax_errors: List[str] = field(default_factory=list)

    def add(self, s: Signal) -> None:
        self.signals.append(s)

    def by_dim(self, dim: str) -> List[Signal]:
        return [s for s in self.signals if s.dimension == dim]


# --- lexicons -----------------------------------------------------------------------------

TARGET_LEX = re.compile(
    r"\b(kpi|quota|leaderboard|csat|nps|satisfaction score|resolution rate|conversion|"
    r"success rate|reward|bonus|you will be (?:scored|evaluated|rewarded|graded|rated)|"
    r"your (?:score|rating|performance)|maximi[sz]e|minimi[sz]e)\b", re.I)
# Audit-domain vocabulary that must NOT count as a performance target for the agent itself.
AUDIT_SCORE_LEX = re.compile(
    r"\b(risk (?:score|rating|level)|likelihood|impact rating|maturity (?:score|level)|"
    r"severity|control (?:score|rating)|rate each (?:finding|control|risk))\b", re.I)
SELF_REF = re.compile(r"\b(you|your|the agent|the assistant|i am|i will|my (?:job|goal|score))\b", re.I)
SOFTEN_FROM = re.compile(r"\b(must|never|always|required|shall|mandatory|only)\b", re.I)
SOFTEN_TO = re.compile(r"\b(should|plausible|where possible|use (?:your )?judg?ement|"
                       r"generally|typically|try to|when reasonable|may)\b", re.I)
INJECTION_LEX = re.compile(
    r"ignore (?:all |the )?(?:previous|prior|above) instructions|disregard .{0,20}instructions|"
    r"you are now|new instructions:|rate this (?:repo|repository|agent)|override.{0,20}(?:rules|policy)",
    re.I)

INSTRUCTION_PATH = re.compile(
    r"(prompt|system|instruction|memory|lesson|reflection|guideline|polic|rules?|persona|"
    r"playbook|claude\.?md|agents\.?md|skill|settings|config)", re.I)
OUTPUT_DIRISH = re.compile(r"\b(output|outputs|report|reports|run|runs|log|logs|cache|tmp|temp|dist|build)\b", re.I)

ESCALATION_LEX = re.compile(r"\b(escalat|human (?:review|approval)|supervisor|refer to|hand[\s-]?off)\b", re.I)
PROHIBITED_CMDS = re.compile(r"\b(rm|sudo|curl|wget|ssh|scp|chmod|chown)\b|pip\s+install")


# --- helpers ------------------------------------------------------------------------------

def _lineset(text: str, pattern: re.Pattern) -> List[int]:
    return [i for i, line in enumerate(text.splitlines(), 1) if pattern.search(line)]


def _is_py(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() == PY


def _is_code(path: str) -> bool:
    suffix = PurePosixPath(path).suffix.lower()
    return suffix == PY or suffix in JSTS


def _is_prompt_text(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in {".md", ".txt", ".prompt"}


def _const_str(node: ast.AST) -> Optional[str]:
    """Best-effort constant string from a literal, f-string parts, or Path()/join."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Div)):
        left, right = _const_str(node.left) or "", _const_str(node.right) or ""
        return f"{left}/{right}" if isinstance(node.op, ast.Div) else left + right
    if isinstance(node, ast.Call):
        return "/".join(filter(None, (_const_str(a) for a in node.args))) or None
    return None


# --- Python AST visitor -------------------------------------------------------------------

class _PyVisitor(ast.NodeVisitor):
    def __init__(self, path: str, out: UnitSignals) -> None:
        self.path = path
        self.out = out
        self.has_llm_call = False
        self.const_paths: Dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        value = _const_str(node.value)
        if value:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.const_paths[target.id] = value
        self.generic_visit(node)

    def _resolve(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name) and node.id in self.const_paths:
            return self.const_paths[node.id]
        return _const_str(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_call(node)
        self.generic_visit(node)

    def _check_call(self, node: ast.Call) -> None:
        func = node.func
        attr = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else "")
        line = node.lineno

        # LLM call site
        if attr in ("create", "parse", "stream", "query", "tool_runner") or attr == "messages":
            self.has_llm_call = True

        # Write sinks (D2 / RF1)
        is_open_write = attr == "open" or (isinstance(func, ast.Name) and func.id == "open")
        if is_open_write and len(node.args) >= 2:
            mode = _const_str(node.args[1]) or ""
            if any(m in mode for m in ("w", "a", "x")):
                self._write_sink(self._resolve(node.args[0]), line)
        if attr in ("write_text", "write_bytes") and isinstance(func, ast.Attribute):
            self._write_sink(self._resolve(func.value), line)
        # Note: json.dump(obj, handle) is not a separate sink — its handle comes from an open()
        # call that is visited in its own right, so the path is captured there.

        # Permission creep (D5)
        if attr in ("run", "call", "Popen", "check_output", "check_call") and _is_subprocessish(func):
            level = 4
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    level = 5
            self.out.add(Signal("D5", "subprocess", self.path, line, level, "high",
                                 "spawns a subprocess"))
            self.out.action_capable = True
        if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
            self.out.add(Signal("D5", func.id, self.path, line, 5, "high",
                                 f"{func.id}() on a dynamic value"))
        if attr in ("remove", "unlink", "rmtree"):
            self.out.add(Signal("D5", "delete", self.path, line, 4, "medium", "deletes files"))
            self.out.action_capable = True
        if attr in ("post", "put", "patch", "delete") and _is_httpish(func):
            self.out.add(Signal("D5", "network_write", self.path, line, 4, "medium",
                                 "writes over the network"))
            self.out.action_capable = True
        if attr in ("sendmail", "send_message") or (isinstance(func, ast.Attribute) and attr == "send"):
            self.out.add(Signal("D5", "message_send", self.path, line, 4, "low", "sends a message"))

        # Guard functions (C1)
        if attr in ("guard", "validate", "enforce", "check", "approve", "deny", "allow", "limit"):
            self.out.add(Signal("C1", "guard_call", self.path, line, 3, "low",
                                 f"calls {attr}()", mitigates=True))

    def _write_sink(self, target: Optional[str], line: int, indirect: bool = False) -> None:
        if not target:
            self.out.add(Signal("D2", "write_unresolved", self.path, line, 2, "low",
                                 "writes to a path computed at runtime"))
            return
        if OUTPUT_DIRISH.search(target) and not INSTRUCTION_PATH.search(target):
            return
        if INSTRUCTION_PATH.search(target):
            self.out.add(Signal("D2", "write_instruction_path", self.path, line, 4,
                                 "medium" if not indirect else "low",
                                 f"writes to instruction/memory path ({target})"))


def _is_subprocessish(func: ast.AST) -> bool:
    if isinstance(func, ast.Attribute):
        root = func.value
        if isinstance(root, ast.Name) and root.id in ("subprocess", "os"):
            return True
        return func.attr in ("Popen", "check_output", "check_call") or func.attr == "run"
    return False


def _is_httpish(func: ast.AST) -> bool:
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.value.id in ("requests", "httpx", "session", "client")
    return False


# --- per-file analysis --------------------------------------------------------------------

def _analyze_py(path: str, text: str, out: UnitSignals) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        out.syntax_errors.append(path)
        return False
    visitor = _PyVisitor(path, out)
    visitor.visit(tree)
    return visitor.has_llm_call


def _analyze_jsts(path: str, text: str, out: UnitSignals) -> None:
    for line in _lineset(text, re.compile(r"child_process|\bexec\(|execSync|spawn\(")):
        out.add(Signal("D5", "subprocess", path, line, 4, "low", "child process (JS)"))
        out.action_capable = True
    for line in _lineset(text, re.compile(r"fs\.(?:writeFile|appendFile|writeFileSync)")):
        out.add(Signal("D2", "write_fs", path, line, 3, "low", "filesystem write (JS)"))
    for line in _lineset(text, re.compile(r"""method:\s*['"](?:POST|PUT|PATCH|DELETE)['"]""", re.I)):
        out.add(Signal("D5", "network_write", path, line, 4, "low", "network write (JS)"))
        out.action_capable = True


# --- text / prompt signals ----------------------------------------------------------------

def _analyze_prompt_text(path: str, text: str, out: UnitSignals, agent_written: bool) -> None:
    for line in _lineset(text, TARGET_LEX):
        row = text.splitlines()[line - 1]
        if AUDIT_SCORE_LEX.search(row) and not SELF_REF.search(row):
            continue
        level = 4 if SELF_REF.search(row) else 3
        out.add(Signal("D1", "target_in_prompt", path, line, level,
                       "medium" if level == 4 else "low", "performance target in instructions"))
    for line in _lineset(text, INJECTION_LEX):
        # Injection-like text sitting in repo docs is an informational observation, not an
        # untrusted-input driver: it does not mean the agent ingests untrusted input at runtime.
        out.add(Signal("INJ", "injection_text", path, line, 1, "high",
                       "injection-like directive in repo text"))
    if agent_written:
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if SOFTEN_TO.search(line) and SOFTEN_FROM.search(line):
                out.add(Signal("D2", "softening", path, i, 4, "low",
                               "softened rule wording in agent-written notes"))


# --- untrusted input (D4) and controls from whole-unit text -------------------------------

UNTRUSTED_SRC = re.compile(
    r"st\.(?:file_uploader|chat_input|text_area)|UploadFile|request\.(?:json|form|files)|"
    r"@app\.(?:post|route)|input\(|imaplib|exchangelib|msgraph|BeautifulSoup|playwright|"
    r"PdfReader|pdfplumber|\bfitz\b|chromadb|faiss|pinecone|langchain.*(?:retriever|vectorstore)|"
    r"req\.body|request\.get_json", re.I)
DELIMIT_HINT = re.compile(r"<untrusted|treat .{0,30}as data|do not (?:follow|obey).{0,30}instructions|"
                          r"```|</?document>|user-provided content", re.I)

LOG_FIELDS = ("model", "prompt_version", "prompt_hash", "prompt_sha", "instruction_version",
              "tool", "tool_call", "input", "output", "outcome")


def finalize(out: UnitSignals, unit_text: str, files: Dict[str, str], multi_turn_hint: bool) -> None:
    """Dimension signals that depend on the whole unit, plus agency profile."""
    # D4 untrusted input
    d4_sources = [p for p, t in files.items() if UNTRUSTED_SRC.search(t)]
    if d4_sources:
        mitigated = bool(DELIMIT_HINT.search(unit_text))
        level = 3 if mitigated else 4
        out.add(Signal("D4", "untrusted_source", d4_sources[0], 1, level,
                       "medium", "ingests external/user input" + (" (delimited)" if mitigated else "")))

    # D5 guardrail cross-check: prohibited commands the agent's own code would run. CI
    # workflows and requirements files legitimately install/clean up, so they are out of scope.
    for path, text in files.items():
        if _is_code(path) and ".github/workflows" not in path and "requirements" not in path.lower():
            for line in _lineset(text, PROHIBITED_CMDS):
                out.add(Signal("D5", "prohibited_command", path, line, 4, "low",
                               "SAAF-guardrail-prohibited command token"))
    # bypass-permission modes
    for path, text in files.items():
        for line in _lineset(text, re.compile(r"bypassPermissions|dangerously-skip-permissions|"
                                              r'permission_mode\s*=\s*["\']bypass', re.I)):
            out.add(Signal("D5", "bypass_permissions", path, line, 5, "high",
                           "permission bypass configured"))

    # C1 allowlist structure (also a D5 mitigation)
    if re.search(r"allow(?:ed|list)", unit_text, re.I) and re.search(r"ALLOWED_\w+|allowlist", unit_text):
        out.add(Signal("C1", "allowlist", _first(files), 1, 3, "low",
                       "tool/command allowlist present", mitigates=True))

    # C1 guard tests
    for path, text in files.items():
        if re.search(r"test", path, re.I) and re.search(r"pytest\.raises|assert.*(?:block|den|reject|raise)", text, re.I):
            out.add(Signal("C1", "guard_test", path, 1, 5, "medium",
                           "test asserts a guard blocks an action", mitigates=True))

    # C2 versioning
    if any(re.search(r"(^|/)prompts?/|prompts?\.py$|system_prompt", p) for p in files):
        out.add(Signal("C2", "prompt_files", _first(files), 1, 3, "low",
                       "prompts kept in dedicated files", mitigates=True))
    if re.search(r"PROMPT_VERSION|prompt_hash|hashlib\.\w+\(.*prompt", unit_text, re.I):
        out.add(Signal("C2", "prompt_versioned", _first(files), 1, 4, "medium",
                       "prompt version or hash recorded", mitigates=True))
    if "CODEOWNERS" in files:
        out.add(Signal("C2", "codeowners", "CODEOWNERS", 1, 5, "low",
                       "CODEOWNERS present", mitigates=True))

    # C3 independent review
    if any(re.search(r"(^|/)tests?/", p) for p in files):
        out.add(Signal("C3", "tests", _first(files), 1, 3, "low", "test suite present", mitigates=True))
    if any(".github/workflows" in p for p in files):
        out.add(Signal("C3", "ci", _first(files), 1, 4, "low", "CI workflow present", mitigates=True))
    if any(re.search(r"(^|/)evals?/", p) for p in files):
        out.add(Signal("C3", "evals", _first(files), 1, 4, "medium", "eval set present", mitigates=True))

    # C4 oversight / rollback
    for path, text in files.items():
        for line in _lineset(text, re.compile(r"input\(.*approv|requires_approval|interrupt_before|"
                                             r"pending_review|dry[_-]?run|MAX_TURNS|max_turns|"
                                             r"max_cycles|kill[_-]?switch|rollback|quarantine", re.I)):
            out.add(Signal("C4", "oversight", path, line, 3, "low",
                           "human-oversight or rollback control", mitigates=True))
            break

    # C5 decision log
    for path, text in files.items():
        if re.search(r"\.jsonl|log\.jsonl|audit_trail|audit_logger|run_logger", path, re.I) or \
           re.search(r"jsonl|audit_trail|append.*log", text, re.I):
            covered = sum(1 for f in LOG_FIELDS if re.search(rf'["\']?{f}["\']?\s*[:=]', text))
            has_version = bool(re.search(r'(prompt_version|prompt_hash|prompt_sha|instruction_version|'
                                         r'\bmodel\b)\s*[:=]', text))
            level = 4 if has_version and covered >= 4 else (3 if covered >= 2 else 2)
            out.add(Signal("C5", "decision_log", path, 1, level, "medium",
                           f"structured log ({covered} fields, version={'yes' if has_version else 'no'})",
                           mitigates=True))
            break

    # agency profile
    out.action_capable = out.action_capable or any(
        s.dimension == "D5" and s.level >= 4 for s in out.signals)
    if out.action_capable:
        out.agency = "autonomous" if not any(s.dimension == "C4" for s in out.signals) else "assisted"
    elif multi_turn_hint:
        out.agency = "assisted"
    else:
        out.agency = "advisory"


def _first(files: Dict[str, str]) -> str:
    return next(iter(files), "")


# --- entry point --------------------------------------------------------------------------

AGENT_WRITTEN_HINT = re.compile(r"(^|/)(memory|lessons?|reflections?|notes)/|lessons?\.(md|txt|json)$", re.I)
MULTI_TURN = re.compile(r"messages\[-?\d|history\[-|append.*messages|conversation|StateGraph|"
                        r"while .*tool_use|runner|chat_loop", re.I)


def run_checks(files: Dict[str, str]) -> UnitSignals:
    out = UnitSignals()
    unit_text_parts = []
    multi_turn = False
    for path, text in files.items():
        unit_text_parts.append(text)
        if MULTI_TURN.search(text):
            multi_turn = True
        if _is_py(path):
            _analyze_py(path, text, out)
        elif _is_code(path):
            _analyze_jsts(path, text, out)
        if _is_prompt_text(path) or _is_py(path):
            _analyze_prompt_text(path, text, out, agent_written=bool(AGENT_WRITTEN_HINT.search(path)))
    finalize(out, "\n".join(unit_text_parts), files, multi_turn)
    return out
