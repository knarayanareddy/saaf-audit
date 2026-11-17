"""The Red Pencil rules.

Each rule matches one weakness pattern found in a SAAF agent repo during the
SAAF Security Challenge (10 November 2026). Rules read source code as text or
as a syntax tree (Python's `ast` module). They never import or run the code
they scan, so scanning a hostile repo is safe.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    severity: str  # "high", "medium" or "low"
    title: str
    why: str
    fix: str
    seen_in: str  # the SAAF finding that motivated the rule


@dataclass(frozen=True)
class Finding:
    rule: Rule
    path: str  # relative path, forward slashes
    line: int
    detail: str


_SECRET_FIX = (
    "Keep secrets on the server: use them there and never pass them to "
    "templates, JSON or HTTP responses."
)

RULES: dict[str, Rule] = {
    r.id: r
    for r in [
        Rule(
            "RP001",
            "jinja-autoescape-off",
            "high",
            "Jinja template rendered with autoescaping off",
            "Model output or document text placed in the page becomes live HTML "
            "or script when someone opens it.",
            "Use jinja2.Environment(autoescape=select_autoescape()) or pass "
            "autoescape=True.",
            "Finding-analysis report/report_generator.py:16",
        ),
        Rule(
            "RP002",
            "secret-sent-to-page",
            "high",
            "Secret from the environment passed to a page or response",
            "Anyone who can load the page or call the endpoint can read the secret.",
            _SECRET_FIX,
            "Finding-analysis app.py:34-35",
        ),
        Rule(
            "RP003",
            "secret-in-template",
            "high",
            "Template prints a secret-looking variable",
            "The value ends up in the page source, even inside a password field.",
            _SECRET_FIX,
            "Finding-analysis templates/index.html:157",
        ),
        Rule(
            "RP004",
            "fixed-delimiter-wrapper",
            "high",
            "Untrusted text wrapped in a fixed tag that the text itself can close",
            "A document containing the closing tag ends the wrapper early, and "
            "the text after it is read as instructions.",
            "Use a random boundary per run, reject or escape it inside the text, "
            "and tell the model the wrapped text is data, never instructions.",
            "Executive-Summary-Writer scripts/material.py:211",
        ),
        Rule(
            "RP005",
            "unbounded-join-into-prompt",
            "medium",
            "Documents joined into a prompt with no boundary",
            "The model cannot tell where one document ends and the instructions "
            "begin, so a planted line can act as an instruction.",
            "Wrap each document in its own random-boundary block and label it as data.",
            "Compliance-Audit-Agent scripts/build_prompt.py:595-601",
        ),
        Rule(
            "RP006",
            "debug-server",
            "medium",
            "Web server started in debug mode",
            "Debug mode shows stack traces and an interactive console to the browser.",
            "Read debug from an environment variable that defaults to off.",
            "Finding-analysis app.py:218",
        ),
        Rule(
            "RP007",
            "dev-reload",
            "low",
            "Development auto-reload enabled in the run script",
            "Auto-reload watches the source tree and restarts on any change; it "
            "is meant for local development only.",
            "Enable reload only through an explicit development flag.",
            "three-way-match-audit webapp/run.py:9",
        ),
        Rule(
            "RP008",
            "path-check-without-resolve",
            "medium",
            "Path containment check without resolve()",
            "Comparing .parent without resolving the path lets '..', symlinks or "
            "odd separators slip past the check.",
            "Use path.resolve().is_relative_to(BASE_DIR.resolve()).",
            "three-way-match-audit webapp/app/main.py:151",
        ),
    ]
}

# ----------------------------------------------------------------------------
# Shared patterns
# ----------------------------------------------------------------------------

# Names that look like secrets. Matched against environment variable names and
# template variable names.
SECRET_WORD = re.compile(
    r"api[_-]?key|secret|token|passw(?:or)?d|credential|private[_-]?key", re.I
)
# Template names that contain a secret word but are not secrets.
NOT_A_SECRET = re.compile(r"csrf", re.I)

# Calls whose arguments end up in a page or an HTTP response.
RESPONSE_CALLS = {
    "render_template",
    "render_template_string",
    "stream_template",
    "jsonify",
    "make_response",
    "Response",
    "HTMLResponse",
    "JSONResponse",
    "TemplateResponse",
    "render",
}

# RP005 only fires when the joined items look like documents or evidence, so
# static tables (GRADES, categories) do not count. Tuned on the SAAF repos.
DOC_WORD = re.compile(
    r"polic|doc|material|evidence|file|page|chunk|text|content|report|source|summar|"
    r"upload|finding|attachment|transcript|email",
    re.I,
)

# A call with one of these words in its name is treated as escaping its input.
ESCAPE_HINTS = ("escape", "fence", "sanitize", "sanitise", "defang", "bleach", "quote", "neutrali")

# Ordinary HTML tags. Wrappers using these are left to the HTML escaping rules.
HTML_TAGS = frozenset(
    """a abbr address article aside b bdi bdo blockquote body br button caption
    cite code col colgroup dd del details dfn div dl dt em fieldset figcaption
    figure font footer form h1 h2 h3 h4 h5 h6 head header hr html i img input
    ins kbd label legend li main mark nav ol optgroup option p pre q s samp
    section select small span strong style sub summary sup table tbody td
    textarea tfoot th thead time title tr u ul var""".split()
)

# <tag attrs> inner </tag>, where the same tag name opens and closes.
WRAP = re.compile(r"<([A-Za-z_][\w:.-]*)\b([^<>]*)>(.*?)</\1\s*>", re.S)

# Placeholders for interpolated values when an f-string is flattened to text.
VALUE_RAW = "\x00R\x00"
VALUE_ESCAPED = "\x00E\x00"

SUPPRESS = re.compile(r"red-pencil:\s*ignore(?:\[([A-Z0-9,\s]+)\])?")


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------


def dotted(node: ast.AST) -> str:
    """Return 'os.environ.get' for the expression os.environ.get, '' if not a name."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _str_const(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_true(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def reads_secret_env(node: ast.AST, secret_vars: set[str]) -> bool:
    """True if the expression reads a secret-named environment variable."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            name = dotted(sub.func)
            if name.endswith("getenv") or name.endswith("environ.get"):
                key = _str_const(sub.args[0]) if sub.args else None
                if key and SECRET_WORD.search(key):
                    return True
        elif isinstance(sub, ast.Subscript) and dotted(sub.value).endswith("environ"):
            key = _str_const(sub.slice)
            if key and SECRET_WORD.search(key):
                return True
        elif isinstance(sub, ast.Name) and sub.id in secret_vars:
            return True
    return False


def _is_newline_join(node: ast.AST) -> bool:
    """True for "\\n".join(...) style calls: whole documents glued together."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        sep = _str_const(node.func.value)
        return node.func.attr == "join" and sep is not None and "\n" in sep
    return False


def _is_document_join(node: ast.AST) -> bool:
    """A newline join over something whose name suggests documents or evidence."""
    if not _is_newline_join(node) or not node.args:  # type: ignore[attr-defined]
        return False
    return bool(DOC_WORD.search(ast.unparse(node.args[0])))  # type: ignore[attr-defined]


def _looks_escaped(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            name = dotted(sub.func).lower()
            if any(hint in name for hint in ESCAPE_HINTS):
                return True
    return False


def suppressed(line_text: str, rule_id: str) -> bool:
    """A finding is skipped when its line carries `red-pencil: ignore[RPxxx]`."""
    m = SUPPRESS.search(line_text)
    if not m:
        return False
    if m.group(1) is None:
        return True
    return rule_id in {part.strip() for part in m.group(1).split(",")}


# ----------------------------------------------------------------------------
# Python files
# ----------------------------------------------------------------------------


@dataclass
class _ModuleFacts:
    jinja_names: dict[str, str] = field(default_factory=dict)  # local name -> jinja2 name
    jinja_modules: set[str] = field(default_factory=set)  # local names for the jinja2 module
    secret_vars: set[str] = field(default_factory=set)  # names assigned from a secret env var
    joined_vars: set[str] = field(default_factory=set)  # names assigned from "\n".join(...)
    escaped_vars: set[str] = field(default_factory=set)  # names assigned from an escaping call


def _module_facts(tree: ast.AST) -> _ModuleFacts:
    facts = _ModuleFacts()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "jinja2":
            for alias in node.names:
                facts.jinja_names[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "jinja2":
                    facts.jinja_modules.add(alias.asname or alias.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if not names:
                continue
            if reads_secret_env(node.value, set()):
                facts.secret_vars.update(names)
            if _is_document_join(node.value):
                # ALL_CAPS names are constants by convention, not documents.
                facts.joined_vars.update(n for n in names if not n.isupper())
            if _looks_escaped(node.value):
                # text = _neutralize_tags(...) on an earlier line (Vendor_Guard), a false alarm in v0.1
                facts.escaped_vars.update(names)
    return facts


class _PythonChecker(ast.NodeVisitor):
    def __init__(self, facts: _ModuleFacts) -> None:
        self.facts = facts
        self.hits: list[tuple[str, int, str]] = []  # (rule id, line, detail)

    # -- calls ---------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        self._jinja_autoescape(node)
        self._secret_to_response(node)
        self._dev_server(node)
        self.generic_visit(node)

    def _jinja_autoescape(self, node: ast.Call) -> None:
        fn = node.func
        original = None
        if isinstance(fn, ast.Name):
            original = self.facts.jinja_names.get(fn.id)
        elif (
            isinstance(fn, ast.Attribute)
            and isinstance(fn.value, ast.Name)
            and fn.value.id in self.facts.jinja_modules
        ):
            original = fn.attr
        if original not in ("Template", "Environment"):
            return
        kwargs = {k.arg: k.value for k in node.keywords if k.arg}
        autoescape = kwargs.get("autoescape")
        if autoescape is None or (
            isinstance(autoescape, ast.Constant) and autoescape.value is False
        ):
            self.hits.append(("RP001", node.lineno, f"jinja2.{original}(...) without autoescape"))

    def _secret_to_response(self, node: ast.Call) -> None:
        name = dotted(node.func).rsplit(".", 1)[-1]
        if name not in RESPONSE_CALLS:
            return
        for value in [*node.args, *(k.value for k in node.keywords)]:
            # bool(os.getenv("API_KEY")) only reveals whether a key is set.
            if isinstance(value, ast.Call) and dotted(value.func) in ("bool", "len"):
                continue
            if reads_secret_env(value, self.facts.secret_vars):
                self.hits.append(
                    ("RP002", node.lineno, f"{name}(...) receives a secret read from the environment")
                )
                return

    def _dev_server(self, node: ast.Call) -> None:
        name = dotted(node.func)
        if not (name == "run" or name.endswith(".run")):
            return
        kwargs = {k.arg: k.value for k in node.keywords if k.arg}
        if _is_true(kwargs.get("debug")):
            self.hits.append(("RP006", node.lineno, f"{name}(debug=True)"))
        for key in ("reload", "use_reloader"):
            if _is_true(kwargs.get(key)):
                self.hits.append(("RP007", node.lineno, f"{name}({key}=True)"))

    # -- assignments -----------------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "debug" and _is_true(node.value):
                self.hits.append(("RP006", node.lineno, f"{dotted(target)} = True"))
        self.generic_visit(node)

    # -- comparisons -------------------------------------------------------------

    def visit_Compare(self, node: ast.Compare) -> None:
        if any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
            operands = [node.left, *node.comparators]
            has_parent = any(isinstance(o, ast.Attribute) and o.attr == "parent" for o in operands)
            looks_like_path = any(
                re.search(r"path|dir|file|folder", dotted(o), re.I) for o in operands
            )
            resolved = any(
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr in ("resolve", "realpath", "abspath")
                for o in operands
                for sub in ast.walk(o)
            )
            if has_parent and looks_like_path and not resolved:
                self.hits.append(
                    ("RP008", node.lineno, "path compared via .parent without resolve()")
                )
        self.generic_visit(node)

    # -- f-strings ---------------------------------------------------------------

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        # Flatten the f-string to text, with a placeholder for each value.
        pieces: list[str] = []
        joined_positions: list[int] = []
        position = 0
        constant_length = 0
        for value in node.values:
            if isinstance(value, ast.Constant):
                text = str(value.value).replace("\x00", "")
                constant_length += len(text)
            elif isinstance(value, ast.FormattedValue):
                escaped = _looks_escaped(value.value) or (
                    isinstance(value.value, ast.Name) and value.value.id in self.facts.escaped_vars
                )
                text = VALUE_ESCAPED if escaped else VALUE_RAW
                if _is_document_join(value.value) or (
                    isinstance(value.value, ast.Name) and value.value.id in self.facts.joined_vars
                ):
                    joined_positions.append(position)
            else:
                text = ""
            pieces.append(text)
            position += len(text)
        flat = "".join(pieces)
        # Whole XML documents (config files, SVG) are not prompts.
        is_xml_document = re.search(r"<\?xml|<!doctype", flat, re.I) is not None

        wrapped_spans: list[tuple[int, int]] = []
        reported = is_xml_document
        for m in WRAP.finditer(flat):
            wrapped_spans.append(m.span())
            tag = m.group(1)
            if reported or tag.lower() in HTML_TAGS:
                continue
            if VALUE_RAW in m.group(2) or VALUE_RAW in m.group(3):
                self.hits.append(
                    ("RP004", node.lineno, f"<{tag}> ... </{tag}> around interpolated text")
                )
                reported = True

        # Documents glued with newlines and dropped into a prompt-sized text.
        if constant_length >= 40:
            for pos in joined_positions:
                if not any(start < pos < end for start, end in wrapped_spans):
                    self.hits.append(
                        ("RP005", node.lineno, "newline-joined text interpolated with no boundary")
                    )
                    break
        self.generic_visit(node)


def check_python(source: str) -> list[tuple[str, int, str]]:
    """Return (rule id, line, detail) hits for one Python file. Raises SyntaxError."""
    tree = ast.parse(source)
    checker = _PythonChecker(_module_facts(tree))
    checker.visit(tree)
    return checker.hits


# ----------------------------------------------------------------------------
# HTML and Jinja templates
# ----------------------------------------------------------------------------

_TEMPLATE_EXPR = re.compile(r"\{\{(.*?)\}\}")


def check_template(source: str) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for number, line in enumerate(source.splitlines(), start=1):
        for m in _TEMPLATE_EXPR.finditer(line):
            expression = m.group(1).strip()
            variable = expression.split("|", 1)[0]
            if SECRET_WORD.search(variable) and not NOT_A_SECRET.search(variable):
                hits.append(("RP003", number, "{{ " + expression + " }}"))
    return hits
