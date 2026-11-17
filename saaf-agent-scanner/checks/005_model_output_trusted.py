"""SAAF-005: an LLM answer is parsed (json.loads / regex) and its decision fields (verdict, status, score, rating,
control_id, owner, hours, conclusion, risk ...) flow into the result without schema validation, enum/range checks or
cross-checking against source data.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, snippet

CHECK = {
    "id": "SAAF-005",
    "slug": "model-output-trusted-unvalidated",
    "category": "integrity-of-audit-conclusion",
    "severity": "Medium",
    "title": "Model output is parsed and its verdict/score/owner fields are used without schema or consistency validation",
    "intended": "The audit conclusion is computed or confirmed by deterministic logic; model output only proposes values that "
                "are checked against an allowed set, a numeric range and the source data (RCM, evidence, control list) "
                "before they enter the report.",
    "actual": "The model reply is parsed with json.loads() or a regex and decision fields such as verdict, status, score, "
              "rating, control_id, owner, hours or conclusion are read (often with a permissive default) and stored or "
              "reported as-is. No pydantic/jsonschema validation, enum or range check, or comparison with the trusted "
              "input is present in the same function.",
    "impact": "A model slip or a prompt injection in the audited material can return an invented status ('PASS-ish'), a "
              "missing key that defaults to N-A, a negative hours value, or another control's id; the unvalidated value "
              "is counted and reported as the audit conclusion, so a failing control can look clean and the "
              "independence and resource checks can be evaded.",
    "recommendation": "Validate the parsed reply against a strict schema (pydantic/jsonschema or the API's structured-output "
                      "mode): required keys, verdict/status in a fixed enum, numbers within a range, ids equal to the "
                      "requested id; overwrite identity fields (control_id, owner, report_id) from trusted data; treat a "
                      "missing or invalid field as 'not assessed / manual review' rather than a default pass or N-A.",
    "refs": "CWE-20, CWE-345, CWE-1287, OWASP LLM05 (Improper Output Handling), OWASP LLM09",
}

LLM_CALL = re.compile(
    r"messages\.create\(|chat\.completions\.create\(|responses\.create\(|\.generate_content\(|\.invoke\(|\.ainvoke\(|"
    r"\.chat\(\s*model|litellm\.completion\(|\bcompletion\(\s*model|ollama\.(chat|generate)\(|client\.models\.generate|"
    r"call_claude\w*\(|call_llm\w*\(|ask_llm\w*\(|query_llm\w*\(|llm_call\w*\(|_call_model\(|\bllm\.(complete|predict)\(|"
    r"\.beta\.messages\.|messages\.stream\(|\.content\[0\]\.text|choices\[0\]\.message\.content|\.output_text|"
    r"\.generate\(\s*(prompt|messages)")
LLM_FILE = re.compile(r"anthropic|openai|litellm|ollama|langchain|bedrock|genai|mistralai|cohere|gpt-|claude-", re.I)
PARSE = re.compile(r"\bjson\.loads\(|\bloads\(|_?extract_json\w*\(|_?parse_\w*json\w*\(|json_repair|"
                   r"ast\.literal_eval\(|\.json\(\)")
MODEL_VAR = re.compile(r"raw|resp|text|content|output|reply|completion|answer|llm|message|result|body|payload|json_str|"
                       r"cleaned|stripped", re.I)
# decision fields, accessed as ["k"] / .get("k") on parsed data
FIELDS = (r"verdict|status|score|rating|risk(?:_rating|_level|_score)?|severity|control_id|owner|control_owner|"
          r"assigned_to|estimated_hours|hours|conclusion|opinion|result|outcome|compliance|compliant|effectiveness|"
          r"confidence|found|sufficient|decision|priority|risk_id|report_id|passed|pass|"
          r"\w+_(?:score|rating|verdict|level|hours|owner)")
ACCESS = re.compile(r"(\w+)\s*(?:\.get\(\s*|\[\s*)[\"'](" + FIELDS + r")[\"']")
SPREAD = re.compile(r"\*\*\s*(?:data|result|parsed|verdict|obj|output|resp\w*|answer|reply|llm\w*)\b")
REGEX_FIELD = re.compile(r"re\.(?:search|match|findall|finditer)\(\s*r?[\"'][^\"']*\b(?:verdict|rating|status|score|"
                         r"risk|conclusion|severity|compliance)\b(?![^\"']*\((?:\?:)?[A-Za-z-]+(?:\|[A-Za-z-]+)+\))", re.I)
# membership test on a decision field: `if verdict not in ALLOWED`, `assert data["status"] in {...}`
MEMBER = re.compile(r"\b(?:if|elif|assert|while)\b[^\n]*(?:%s)[^\n]*(?:\b(?:not\s+)?in\s+[\{\(\[]|"
                    r"\bin\s+(?:self\.)?(?:[A-Z][A-Z0-9_]{2,}|(?i:\w*(?:allowed|valid|enum|known|expected|levels|verdicts|"
                    r"statuses|ratings|choices)\w*))\b)" % FIELDS)
# anything that counts as validation / cross-checking in the same function
GUARD = re.compile(
    r"model_validate|parse_obj|TypeAdapter|\bjsonschema\b|\bvalidate\w*\(|\.validate\(|Draft\d+Validator|"
    r"\b(?:if|elif|assert)\b[^\n]*(?:==|!=)\s*(?:control_id|ctrl_id|custom_id|expected\w*|requested\w*)|"
    r"\bEnum\b|\bLiteral\[|\.issubset\(|\bset\(\w+\)\s*[<>=-]|\.keys\(\)\s*[<>=-]|\bmissing\s*=|\bclamp\w*\(|"
    r"(?:min|max)\(\s*[\d.]+\s*,|(?:min|max)\([^\n]*,\s*[\d.]+\s*\)|\b(?:int|float)\(\s*\w+[^\n]*\)\s*(?:<|>|<=|>=)\s*\d|"
    r"\b\w*(?:normali[sz]e|sanitize|coerce|enforce|reconcile|cross_?check)\w*\(|\.upper\(\)\s+not\s+in|"
    r"\.lower\(\)\s+not\s+in|\bpydantic\b|BaseModel|\b\w+Model\(\*\*|dataclass", re.I)
# overwritten with trusted value before use e.g. data["control_id"] = control_id
OVERWRITE = re.compile(r"\[\s*[\"'](?:%s)[\"']\s*\]\s*=\s*(?!\s*(?:data|result|parsed)\b)" % FIELDS)


_DEF = re.compile(r"^(\s*)(?:async\s+def|def)\s+\w+")


def functions(lines):
    """Like _lib.functions but ignores lines inside triple-quoted strings (prompts often start at column 0)."""
    inside, quote, mask = False, "", []
    for l in lines:
        mask.append(inside)
        for m in re.finditer(r'\"\"\"|\'\'\'', l):
            if not inside:
                inside, quote = True, m.group(0)
            elif m.group(0) == quote:
                inside = False
    defs = [(i, len(m.group(1))) for i, l in enumerate(lines) if not mask[i] and (m := _DEF.match(l))]
    for i, ind in defs:
        j = i + 1
        while j < len(lines):
            l = lines[j]
            if (not mask[j] and l.strip() and (len(l) - len(l.lstrip())) <= ind
                    and not l.lstrip().startswith(("#", ")", "]", "}"))):
                break
            j += 1
        yield i, j, lines[i].strip()


NOT_MODEL_ARG = re.compile(r"read_text|\.read\(|open\(|argv|Path\(|stdin|environ|request\.|file", re.I)


def _parse_line(lines, a, b):
    """First line in [a, b) that parses a model-looking value (not a file, argv or request body)."""
    for i in range(a, b):
        m = PARSE.search(lines[i])
        if not m or re.match(r"\s*(?:async\s+)?def\b", lines[i]):
            continue
        arg = lines[i][m.end():m.end() + 80]
        if MODEL_VAR.search(arg) and not NOT_MODEL_ARG.search(arg.split(")")[0]):
            return i
    return None


def _first(rx, lines, a, b):
    return next((i for i in range(a, b) if rx.search(lines[i])), None)


PARSED_VAR = re.compile(r"^\s*(\w+)\s*(?::[^=]+)?=\s*[^\n]*(?:%s)" % PARSE.pattern)
SINK = re.compile(r"\b(?:format_report|render\w*|build_report\w*|generate_report\w*|write_report\w*|save\w*|store\w*|"
                  r"to_markdown|to_excel|to_docx|to_html|\w*report\w*|\w*scorecard\w*|Assessment|Verdict\w*|Finding\w*)\s*\(")
DECISION_WORDS = re.compile(r"\b(?:verdict|rating|severity|compliance|scorecard|risk[_ ]rating|PASS|FAIL|WARN|"
                            r"effectiveness|conclusion)\b|\"status\"", re.I)


def _flows_to_report(lines, a, b, pl, body, text):
    """Parsed model JSON handed whole to a report/record builder (e.g. format_report(audit_result)), in a file whose prompts/records are about verdicts/ratings."""
    m = PARSED_VAR.match(lines[pl])
    if not m or not DECISION_WORDS.search(text):
        return None, None
    var = m.group(1)
    use_rx = re.compile(r"\b%s\b" % re.escape(var))
    for i in range(pl + 1, b):
        l = lines[i]
        if use_rx.search(l) and SINK.search(l):
            return i, "report"
    return None, None


STRICT_FIELDS = re.compile(r"(?:\.get\(\s*|\[\s*)[\"'](verdict|rating|risk_rating|control_id|control_owner|assigned_to|estimated_hours|conclusion|"
                           r"effectiveness|severity|compliance|sufficient|risk_id|opinion)[\"']")
FILE_GUARD = re.compile(r"model_validate|parse_obj|TypeAdapter|\bjsonschema\b|\bpydantic\b|BaseModel|Draft\d+Validator|"
                        r"def\s+(?:validate|_validate|check_\w*schema)\w*\(", re.I)


def _cross_function(text, lines, a, b, pl):
    """Parse happens here, the decision fields are consumed elsewhere in the same file (e.g. batch results parsed in
    one function, entry['control_owner'] / entry['estimated_hours'] read by the checks). No validator anywhere in the file."""
    if FILE_GUARD.search(text) or MEMBER.search(text):
        return None
    if not re.match(r"\s*(?:return\b|(?:results?|out\w*|entries|entry|responses?|parsed)\s*(?:\[[^\]]+\]\s*)?(?:=|\.append\())\s*[^\n]*"
                     + "(?:" + PARSE.pattern + ")", lines[pl]):
        return None
    fields = {m.group(1) for m in STRICT_FIELDS.finditer(text)}
    if len(fields) < 3:
        return None
    return pl


ID_THEN_SPREAD = re.compile(r"\{\s*[\"'](?:\w*id|control_id|report_id|owner)[\"']\s*:[^{}]*,\s*\*\*\s*(\w+)\s*\}")


def _id_overwritten_by_spread(text, lines):
    """{"control_id": control_id, **verdict}: the model dict is spread AFTER the trusted id, so a model-supplied
    control_id/owner key replaces it. Only in files that parse model output and never check the keys."""
    if FILE_GUARD.search(text) or not (LLM_CALL.search(text) and _parse_line(lines, 0, len(lines)) is not None):
        return None
    for i, l in enumerate(lines):
        m = ID_THEN_SPREAD.search(l)
        if m and not re.search(r"\b%s\b[^\n]*\.pop\(|\.keys\(\)\s*-|-\s*\w+\.keys\(\)\s*==|\bdel\s+%s\[" % (m.group(1), m.group(1)), text):
            return i
    return None


def run(repo):
    hits, seen = [], set()
    for rel in repo.files({".py"}):
        text = repo.read(rel)
        if not (LLM_FILE.search(text) and (PARSE.search(text) or REGEX_FIELD.search(text))):
            continue
        lines = repo.lines(rel)
        i = _id_overwritten_by_spread(text, lines)
        if i is not None:
            hits.append(Hit(rel, i + 1, snippet(lines[i]),
                            "model-parsed dict is spread after the trusted id key, so a model-supplied id/owner key "
                            "overrides it; keys are not validated"))
            seen.add((rel, "file"))
        for a, b, head in functions(lines):
            body = "\n".join(lines[a:b])
            if b - a > 400:
                continue
            if not (LLM_CALL.search(body) or re.search(r"\bdef\s+\w*(?:parse|extract)\w*(?:response|reply|output|verdict|llm|json)\w*\(", head, re.I)):
                continue
            pl = _parse_line(lines, a, b)
            regex_variant = False
            if pl is None:
                pl = _first(REGEX_FIELD, lines, a, b)
                regex_variant = pl is not None
                if pl is None:
                    continue
            # the parsed value must be accessed for a decision field, or spread into a record
            use = None
            if regex_variant:
                use = pl
            else:
                for i in range(pl, b):
                    if ACCESS.search(lines[i]) or SPREAD.search(lines[i]):
                        use = i
                        break
            via = None
            if use is None:
                use, via = _flows_to_report(lines, a, b, pl, body, text)
                if use is None:
                    use = _cross_function(text, lines, a, b, pl)
                    via = "file" if use is not None else None
                if use is None:
                    continue
            if GUARD.search(body) or MEMBER.search(body) or OVERWRITE.search(body):
                continue
            fields = sorted({m.group(2) for l in lines[pl:b] for m in ACCESS.finditer(l)})
            read = ("read via " + ", ".join(fields[:5])) if fields else (
                "" if via else "spread into a record")
            what = ("regex-extracted" if regex_variant else "json-parsed") + " model output" + (
                {"report": " passed whole into a report/record", "file": " stored and consumed by other functions in the file"}.get(via, ""))
            if (rel, use) in seen or (via == "file" and (rel, "file") in seen):
                continue
            seen.add((rel, use))
            seen.add((rel, via))
            hits.append(Hit(rel, use + 1, snippet(lines[use]),
                            f"{head[:60]}: {what} {read} with no schema/enum/range/"
                            f"cross-check {'anywhere in the file' if via == 'file' else 'in the function'}"))
    return hits
