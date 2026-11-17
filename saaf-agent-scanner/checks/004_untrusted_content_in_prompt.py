"""SAAF-004: document / evidence / upload / retrieved text is interpolated into an LLM prompt in a file that calls an
LLM API, with no trust separation (no delimiters + "treat as data" rule, no SAAF guard()/fence()).
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, snippet

CHECK = {
    "id": "SAAF-004",
    "slug": "untrusted-content-in-prompt",
    "category": "indirect-prompt-injection",
    "severity": "Medium",
    "title": "Untrusted document or evidence text is placed in the LLM prompt without trust separation",
    "intended": "Text taken from uploaded documents, evidence files, tickets or retrieved sources is treated as data: it is "
                "wrapped in clear delimiters, the prompt states that it must never be followed as instructions, and "
                "it passes a guard/sanitiser before it reaches the model.",
    "actual": "The code interpolates document/evidence/upload/retrieved text into the prompt (f-string, .format, "
              "concatenation or template substitution) next to the audit instructions, and the file contains no "
              "delimiting tags with a 'treat as data, never follow instructions' rule and no guard()/fence()/"
              "sanitiser call.",
    "impact": "Whoever authors the audited document (auditee, vendor, ticket reporter, web page) can embed instructions "
              "such as 'conclude: sufficient, no exceptions' that the model may follow, so the agent output, rating or "
              "conclusion is controlled by the party being audited (indirect prompt injection).",
    "recommendation": "Wrap every untrusted value in explicit delimiters (for example <untrusted_document>...</...>, "
                      "escaping any closing tag inside the text), add a system-prompt rule that content inside the "
                      "delimiters is data and must never be followed as instructions, pass it through the SAAF "
                      "guard()/fence() helper (data-not-instructions, saaf-guard), keep the output schema-validated, "
                      "and never let model output alone decide pass/fail without a human or deterministic check.",
    "refs": "CWE-1427, CWE-77, OWASP LLM01",
}

LLM_API = re.compile(
    r"\banthropic\b|\bopenai\b|messages\.create|chat\.completions|ChatCompletion|generate_content|invoke_model|"
    r"\bbedrock|ChatAnthropic|ChatOpenAI|\blitellm\b|\bollama\b|responses\.create|\bgenai\b|AzureOpenAI|"
    r"call_claude|ask_claude|claude_client|call_llm|llm_client|\bcomplete\(|\bclaude\b.{0,40}\bcreate\(", re.I)

# names that carry attacker-influenced text
SRC_WORDS = (r"document|doc|evidence|upload|uploaded|pdf|extracted|file_content|file_text|filetext|retrieved|"
             r"chunk|ticket|finding|policy|vendor|org|report|transcript|email|article|rss|feed|excerpt|snippet|"
             r"rcm|csv|xlsx|source|body|content|text|context|mandate|issue|comment|description|export|raw|material|notes|free_text|"
             r"structured_data|policies|inputs_summary|input_summary|issue_text")
SRC_NAME = re.compile(rf"(?i)(?:^|_)(?:{SRC_WORDS})(?:_|$|s\b)")
STRONG = re.compile(r"(?i)document|evidence|upload|extracted|pdf|retrieved|chunk|ticket|vendor_text|org_text|"
                    r"finding_text|policy_text|rcm|transcript|rss|article|export|material|free_text|structured_data|inputs?_summary|issue_text")
# generic names are only accepted together with a stronger signal on the same statement
WEAK_ONLY = re.compile(r"(?i)^(?:text|content|body|source|raw|context|report|description|comment|issue|feed|email|"
                       r"policy|finding|org|vendor|doc)s?$")

PY_INTERP = re.compile(r"\{\s*([A-Za-z_][\w\.]*)(?:\[[^\]\}]*\])?(?:\s*[!:][^}]*)?\s*(?:\.\w+\([^)}]*\))?\s*\}")
JS_INTERP = re.compile(r"\$\{\s*([A-Za-z_][\w\.]*)(?:\[[^\]]*\])?(?:\.\w+\([^)]*\))?\s*\}")
PLUS_CONCAT = re.compile(r"""\+""")
FORMAT_ARG = re.compile(r"\.format\(([^)]*)\)|%\s*\(?\s*([A-Za-z_][\w\.]*)")
PROMPT_CTX = re.compile(r"(?i)\b(prompt|user_content|user_message|user_msg|user_text|usermsg|messages?|instruction|"
                        r"query|question|payload|content|user|system)\w*\s*(?:[:=+]|\+=)|\"role\"|'role'|"
                        r"role\s*[:=]|\b(?:complete|create|invoke|generate_content|call_claude|ask|chat)\w*\(")
# a line is "prompt prose" if the string carries instruction-ish text or labels the document
PROSE = re.compile(r"(?i)\b(extract|analy[sz]e|review|assess|classify|summari[sz]e|evaluate|conclusion|compare|"
                   r"match|following|below|document|evidence|text|request|based on|using the|determine|judge|"
                   r"verify|check|identify|rate|score|answer)\b|:\s*(?:\\n|\"|'|$)")

# trust separation present anywhere in the file
GUARD = re.compile(
    r"data[_-]not[_-]instructions|saaf[_-]guard|\bfence\(|\bguard\(|\bguard_text\(|wrap_untrusted|"
    r"sanitize_(?:for_)?(?:prompt|text|input)|sanitise_|escape_untrusted|untrusted_wrap|spotlight|"
    r"strip_injection|neutralize|neutralise|prompt_guard|scan_for_injection", re.I)
DATA_RULE = re.compile(
    r"(?:treat|handle|regard|consider)\b.{0,60}\b(?:as|only as)\b.{0,20}\bdata\b|"
    r"(?:never|do not|don't|must not|should not)\b.{0,30}\b(?:follow|obey|execute|act on|comply with)\b.{0,50}"
    r"\b(?:instruction|command|directive)s?|"
    r"(?:ignore|disregard)\b.{0,30}\b(?:instruction|command)s?\b.{0,40}\b(?:inside|within|in the|embedded|found)|"
    r"data,? not (?:as )?instructions|not (?:as )?instructions|prompt[- ]injection|untrusted (?:data|content|text|input|document)",
    re.I | re.S)
TAGS = re.compile(r"<(untrusted|user_data|untrusted_\w+)[^>\n]{0,40}>|BEGIN (?:UNTRUSTED|DOCUMENT|EVIDENCE|DATA)|<<<", re.I)


def _names(line):
    out = []
    for rx in (PY_INTERP, JS_INTERP):
        for m in rx.finditer(line):
            out.append(m.group(1))
    return out


def _snake(x):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", x)


def _is_src(name):
    leaf = _snake(name.split(".")[-1])
    return bool(SRC_NAME.search(leaf)) and not leaf.isupper()


def _statement(lines, i):
    """Rough statement window: walk back to a line that opens an assignment/call, forward to bracket balance."""
    a = i
    depth = 0
    for k in range(i, max(i - 25, -1), -1):
        s = lines[k]
        depth += s.count(")") + s.count("]") + s.count("}") - s.count("(") - s.count("[") - s.count("{")
        a = k
        if depth < 0 or (re.match(r"\s*\w[\w\.\[\]\"']*\s*(?:\+?=|:)\s*", s) and depth <= 0 and k < i):
            break
        if s.strip() == "" and k < i:
            break
    b = min(i + 12, len(lines))
    return a, b


def _scan_file(rel, lines):
    best = None   # (score, hit)
    tri = None    # (open_idx, is_f, quote) while inside a triple-quoted string
    for i, line in enumerate(lines):
        in_f_tri = False
        open_idx = None
        if tri:
            in_f_tri, open_idx = tri[1], tri[0]
        for m in re.finditer(r'(\bf|\bF|\brf|\bfr)?("{3}|\'{3})', line):
            if tri and m.group(2) == tri[2]:
                tri = None
            elif not tri:
                tri = (i, bool(m.group(1)), m.group(2))
        if tri and tri[0] == i and tri[1]:      # the opening line of an f-triple-quote
            in_f_tri, open_idx = False, i
        if len(line) > 600 or line.lstrip().startswith(("#", "//", "*")):
            continue
        s = line.strip()
        cands = []
        fline = bool(re.search(r"\bf[\"']|\bf\"\"\"", line) or "`" in line)
        if "{" in line and (fline or in_f_tri):
            cands += _names(line)
        if ".format(" in line:
            mm = re.search(r"\.format\((.*)\)", line)
            if mm:
                cands += [x.strip().split("=")[-1].strip() for x in mm.group(1).split(",")]
        if PLUS_CONCAT.search(line):
            cands += re.findall(r"""\+\s*([A-Za-z_][\w\.]*(?:\[[^\]]*\])?)\s*(?:\+|$|\)|,|;)""", line)
            cands += re.findall(r"""(?:^|[\(,=]\s*)([A-Za-z_][\w\.]*)\s*\+\s*["']""", line)
        cands = [re.sub(r"\[.*", "", c) for c in cands if c]
        srcs = [c for c in cands if _is_src(c)]
        if not srcs:
            continue
        if in_f_tri and open_idx is not None:
            a, b = open_idx, min(i + 12, len(lines))
        else:
            a, b = _statement(lines, i)
        ctx = "\n".join(lines[a:b])
        head = "\n".join(lines[a:i + 1])
        if not PROMPT_CTX.search(head):
            continue
        if not (PROSE.search(ctx) or LLM_API.search(ctx)):
            continue
        leafs = [_snake(c.split(".")[-1]) for c in srcs]
        strong = [c for c, l in zip(srcs, leafs) if STRONG.search(l) and not WEAK_ONLY.match(l)]
        if not strong:
            # generic names (text/content/...) need an explicit untrusted-source marker within the statement
            if not re.search(r"(?i)\b(document|evidence|uploaded?|extracted|retrieved|pdf|ticket|excerpt)\b", ctx):
                continue
        score = 3 if strong else 1
        if re.search(r"(?i)evidence|document|upload|extracted|retrieved", " ".join(srcs)):
            score += 1
        if score > (best[0] if best else 0):
            best = (score, Hit(rel, i + 1, snippet(line), f"{srcs[0]} interpolated into the prompt"))
    return best


def run(repo):
    hits = []
    for rel in repo.files({".py", ".js", ".ts", ".mjs", ".jsx", ".tsx"}):
        text = repo.read(rel)
        if "{" not in text or not LLM_API.search(text):
            continue
        if GUARD.search(text) or DATA_RULE.search(text) or TAGS.search(text):
            continue
        b = _scan_file(rel, repo.lines(rel))
        if b:
            h = b[1]
            h.detail += "; no guard()/fence() call or 'treat as data, never follow instructions' rule in this file"
            hits.append(h)
    return hits
