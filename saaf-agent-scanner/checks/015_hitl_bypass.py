"""SAAF-015: a human-review / approval checkpoint is optional, defaults to off, or is decided by the model.
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, functions, snippet

CHECK = {
    "id": "SAAF-015",
    "slug": "human-checkpoint-bypassable",
    "category": "hitl-bypass",
    "severity": "Medium",
    "title": "Human-review checkpoint is optional, off by default, or decided by the model's own output",
    "intended": "AI-generated conclusions, reports, issues or actions only take effect after an identifiable human has "
                "reviewed and approved them, and the approver cannot be the model, a default value or a CLI flag left "
                "on by default.",
    "actual": "The code disables or weakens the checkpoint: an approval flag defaults to approved/auto (auto_approve=True, "
              "skip_review=True, require_human_review=False, approved=True, status='approved' as default), a confirmation "
              "prompt is skipped when stdin is not a TTY or on EOF, a CLI option such as --yes/--no-confirm defaults to on, "
              "or an LLM response field (response[\"approved\"], verdict == \"sufficient\") is used directly to approve, "
              "validate or release an item without any reviewer identity or sign-off step.",
    "impact": "The 'human in the loop' control exists only on paper: model errors, hallucinations or prompt injection "
              "flow straight into approved records, audit conclusions, issues or reports, and automation (CI, cron, "
              "piped stdin) silently bypasses the review that the documentation promises.",
    "recommendation": "Fail closed: default every approval flag to required, refuse to proceed (not auto-approve) when no "
                      "TTY/approver is available, model output may only propose a state such as 'ai_suggested' while a "
                      "separate authenticated reviewer action records approver identity, timestamp and content hash "
                      "before the item becomes approved, and require an explicit per-run opt-in for unattended mode that "
                      "is logged in the audit trail.",
    "refs": "CWE-862, CWE-807, CWE-1188, OWASP LLM06 (Excessive Agency), OWASP LLM09 (Overreliance)",
}

CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
CONF_EXT = {".yaml", ".yml", ".toml", ".env", ".ini", ".cfg"}
COMMENT = re.compile(r"^\s*(#|//|\*|/\*|<!--)")
LLM_CTX = re.compile(r"anthropic|openai|\bllm\b|chat\.completions|messages\.create|ChatCompletion|langchain|"
                     r"generate_content|ollama|litellm|bedrock|\bclaude\b|\bgpt-", re.I)

# --- A: flags that switch the checkpoint off (default value) ---
_OFF_NAMES = r"(?:auto[_-]?approve\w*|auto[_-]?accept\w*|skip[_-]?(?:human|review|approval|confirm\w*|hitl)\w*|" \
             r"no[_-]?(?:human|review|approval|confirm\w*)\w*|bypass[_-]?(?:review|approval|human)\w*|" \
             r"autonomous[_-]?mode|unattended|hitl[_-]?disabled|disable[_-]?(?:human|review|approval|hitl)\w*)"
_REQ_NAMES = r"(?:require[ds]?[_-]?(?:human|review|approval|confirm\w*|sign[_-]?off)\w*|" \
             r"(?:human|manual)[_-]?(?:in[_-]?the[_-]?loop|review|approval|check\w*|gate)\w*|hitl\w*|" \
             r"needs?[_-]?(?:human|review|approval)\w*|ask[_-]?(?:confirm\w*|approval)|confirm[_-]?(?:before|actions?)\w*)"
FLAG_ON = re.compile(rf"""(?ix)(?:^|[\s,{{(\"'])(?:{_OFF_NAMES})["']?\s*(?::\s*[\w\[\]| ]+?\s*)?[:=]\s*(?:True|true|1|["']true["'])\s*[,;)}}]?\s*(?:$|[,)}};#/])""")
FLAG_OFF = re.compile(rf"""(?ix)(?:^|[\s,{{(\"'])(?:{_REQ_NAMES})["']?\s*(?::\s*[\w\[\]| ]+?\s*)?[:=]\s*(?:False|false|0|["']false["'])\s*[,;)}}]?\s*(?:$|[,)}};#/])""")
ENV_OFF = re.compile(r"""(?i)(?:getenv|environ\.get|environ\[|env\.get|process\.env\.)\(?\s*["']?\w*(?:AUTO_?APPROVE|SKIP_?(?:REVIEW|APPROVAL|HUMAN)|"""
                     r"""NO_?CONFIRM)\w*["']?\s*,\s*["']?(?:1|true|yes|on)["']?\s*\)""")
ENV_REQ_OFF = re.compile(r"""(?i)(?:getenv|environ\.get|env\.get|_bool_env|env_bool)\(\s*["']\w*(?:REQUIRE_?(?:HUMAN|REVIEW|APPROVAL)|HUMAN_?(?:REVIEW|APPROVAL)|HITL)\w*["']\s*,\s*(?:False|["']?(?:0|false|no|off)["']?)\s*\)""")
# argparse / click option whose default switches confirmation off
OPT_YES = re.compile(r"""add_argument\(\s*["']--(?:yes|assume-yes|no-confirm\w*|auto-?approve\w*|skip-?(?:review|approval|confirm\w*)|force-?yes)["'][^)]*default\s*=\s*True""", re.I)
CLICK_YES = re.compile(r"""click\.option\(\s*["']--(?:yes|no-confirm\w*|auto-?approve\w*|skip-?(?:review|approval|confirm\w*))["'][^)]*default\s*=\s*True""", re.I)
OPT_NOCONF_STORE_TRUE_DEFAULT = re.compile(r"""add_argument\(\s*["']--confirm["'][^)]*default\s*=\s*False""", re.I)

# --- C: review status defaults to approved ---
DEFAULT_APPROVED = re.compile(
    r"""(?x)^\s*(?:approved|is_approved|human_approved|human_reviewed|reviewed|review_approved|approval|human_review_done)\s*(?::\s*[\w\[\] |]+)?=\s*True\b
       |^\s*(?:\w*(?:review|approval)\w*_status|status|review|approval_state|review_state)\s*(?::\s*[\w\[\] |.]+)?=\s*["'](?:approved|accepted|auto_approved|validated|signed_off|reviewed)["']\s*,?\s*$
       |\.get\(\s*["'](?:approved|is_approved|human_approved|review_approved|reviewed|human_reviewed)["']\s*,\s*True\s*\)
       |\.get\(\s*["']\w*(?:review|approval)\w*["']\s*,\s*["'](?:approved|accepted|auto_approved|reviewed)["']\s*\)
       |\b(?:default\s*=\s*|server_default\s*=\s*|DEFAULT\s+)["']approved["']""")
CLASSY = re.compile(r"^\s*class\s+\w+|@dataclass|BaseModel|Column\(|Field\(|models\.|TypedDict|\bDEFAULTS?\s*=|^\s*(?:def|\w+\s*=\s*dict\()", re.I)

# --- D: confirmation skipped when no TTY / EOF ---
TTY_CHECK = re.compile(r"isatty\(\)|\bsys\.stdin\.closed|except\s+(?:EOFError|\(EOFError[^)]*\))\s*:|os\.isatty|process\.stdin\.isTTY")
APPROVE_RET = re.compile(r"^\s*(?:return\s+(?:True|\"y(?:es)?\"|'y(?:es)?'|\"approve\w*\"|'approve\w*')\b|"
                         r"(?:\w+\s*=\s*(?:True|\"y(?:es)?\"|'y(?:es)?')\b)|"
                         r"(?:auto_?approve\w*|args\.yes|yes)\s*=\s*True\b)")
INPUT_CONF = re.compile(r"\binput\(|click\.confirm\(|Confirm\.ask\(|prompt\(|readline|questionary|inquirer|"
                        r"rl\.question|confirm\(")

# --- B: approval decided by the model output ---
MODEL_VAR = r"(?:conclusion\w*|resp\w*|result\w*|output\w*|llm\w*|verdict\w*|decision\w*|parsed\w*|judge\w*|completion\w*|answer\w*|" \
            r"analysis\w*|review\w*|evaluation\w*|assessment\w*|ai\w*|model\w*|data|obj|out|j|js|payload|reply)"
MODEL_APPROVE = re.compile(
    rf"""^\s*(?:if|elif|while)\s+\(?\s*(?:not\s+)?{MODEL_VAR}\s*(?:\[|\.get\()\s*["'](?:approved|approve|auto_?approve\w*|is_approved|"""
    rf"""safe_to_(?:send|publish|release|post)|ok_to_\w+|can_(?:send|publish|release|post)|release_ok|no_human_review_needed|human_review_not_required|"""
    rf"""needs_human_review_false)["']\s*[\])]?""", re.I)
MODEL_APPROVE_JS = re.compile(
    rf"""^\s*(?:\}}\s*)?(?:if|else if)\s*\(\s*!?\s*{MODEL_VAR}(?:\.|\?\.)(?:approved|isApproved|autoApprove\w*|safeToSend|approve)\b""", re.I)
ACTION = re.compile(r"approv|publish|send|post|create|merge|write|save|submit|finali[sz]e|status|commit|issue|release|"
                    r"validated|accept|return\s+True|mark", re.I)
# model conclusion promoted straight to an approved state
PROMOTE = re.compile(r"""(?:\[\s*["'](?:status|state|review_status|approval_status)["']\s*\]|\.(?:status|state|review_status|approval_status))\s*=\s*["'](?:validated|approved|accepted|verified|signed_off|final\w*|closed|resolved|complete\w*|done)["']""", re.I)
PROMOTE_COND = re.compile(rf"""^\s*(?:if|elif)\s+.*\b{MODEL_VAR}\b.*(?:==|in|\[|\.get\()""", re.I)
REVIEWER_WORDS = re.compile(r"approved_by|reviewer|reviewed_by|confirm\w*|sign[_ -]?off|input\(|\bauditor_id|user_id|current_user|"
                            r"requires?_auth|login_required|is_human|human_decision|manual_review|pending_review|needs_review", re.I)


# advisory escalation flag: set on a result/tool_result but nothing stops the loop afterwards
ESCALATE_FLAG = re.compile(r"""\[\s*["'](?:escalate\w*|needs?_human\w*|requires?_human\w*|human_review_required|hitl\w*)["']\s*\]\s*=\s*True\b""", re.I)
STOPS = re.compile(r"\b(?:break|return|raise|sys\.exit|exit\(|halt|abort|stop|input\(|wait_for|await_human|queue\w*)\b", re.I)


def _emit(hits, rel, ln, line, why):
    hits.append(Hit(rel, ln, snippet(line), why))


def run(repo):
    hits = []
    for rel in repo.files(CODE_EXT | CONF_EXT | {".json"}):
        low = rel.lower()
        base = low.rsplit("/", 1)[-1]
        if base in {"package-lock.json", "tsconfig.json", "composer.json"} or low.endswith((".min.js", ".lock")):
            continue
        txt = repo.read(rel)
        if len(txt) < 20:
            continue
        lines = txt.splitlines()
        is_py = low.endswith(".py")
        is_code = any(low.endswith(e) for e in CODE_EXT)
        found = 0

        for i, line in enumerate(lines):
            if len(line) > 400 or COMMENT.match(line):
                continue
            ln = i + 1
            if FLAG_ON.search(line) and not re.search(r"\bnot\s|\bif\b|==|!=|\bassert\b|\bin\s+\(", line):
                _emit(hits, rel, ln, line, "approval/review gate disabled by default (auto-approve / skip-review flag set to on)")
            elif FLAG_OFF.search(line) and not re.search(r"\bif\b|==|!=|\bassert\b|\bnot\s", line):
                _emit(hits, rel, ln, line, "human-approval requirement defaults to off")
            elif is_code and (ENV_OFF.search(line) or ENV_REQ_OFF.search(line)):
                _emit(hits, rel, ln, line, "environment toggle defaults to skipping human approval")
            elif is_code and (OPT_YES.search(line) or CLICK_YES.search(line)):
                _emit(hits, rel, ln, line, "confirmation-skipping CLI option defaults to on")
            elif is_code and DEFAULT_APPROVED.search(line):
                ctx = "\n".join(lines[max(0, i - 12):i + 1])
                if is_py and not CLASSY.search(ctx) and ".get(" not in line:
                    continue
                if re.search(r"==|!=|\bif\b|\bwhere\b|filter|assert|\bnot\b|\bin\b\s*[\[(]", line):
                    continue
                if re.search(r"\bapproved\b|review|approval|signed_off", line, re.I):
                    _emit(hits, rel, ln, line, "review/approval state defaults to approved")

        if not is_code:
            continue

        # D: non-interactive session approves silently
        if INPUT_CONF.search(txt):
            for i, line in enumerate(lines):
                if COMMENT.match(line) or not TTY_CHECK.search(line):
                    continue
                window = lines[i + 1:i + 5]
                for k, w in enumerate(window):
                    if APPROVE_RET.match(w):
                        # for 'except EOFError:' the approval must be the handler body itself
                        if "EOFError" in line and k > 1:
                            continue
                        _emit(hits, rel, i + 2 + k, w, "confirmation is auto-approved when stdin is not a TTY / EOF")
                        break
                    if w.strip() and (len(w) - len(w.lstrip())) <= (len(line) - len(line.lstrip())) and not w.lstrip().startswith(("else", "elif", "except", "#")):
                        break

        # E: escalate-to-human flag is only advisory data (needs an LLM loop in the same file)
        if LLM_CTX.search(txt):
            for i, line in enumerate(lines):
                if ESCALATE_FLAG.search(line) and not COMMENT.match(line):
                    ind = len(line) - len(line.lstrip())
                    nxt = []
                    for w in lines[i + 1:i + 6]:
                        if w.strip() and (len(w) - len(w.lstrip())) < ind:
                            break  # left the block that sets the flag
                        nxt.append(w)
                    # a stop only counts when it sits in the same block as the flag
                    if not STOPS.search("\n".join(nxt)):
                        _emit(hits, rel, i + 1, line, "escalate-to-human is only a flag in the result; the loop continues and nothing enforces a human stop")

        # B + promote: only in files that talk to an LLM
        if not LLM_CTX.search(txt):
            continue
        if is_py:
            for a, b, head in functions(lines):
                body_lines = lines[a:b]
                body = "\n".join(body_lines)
                if REVIEWER_WORDS.search(body):
                    continue
                for off, l in enumerate(body_lines):
                    i = a + off
                    if MODEL_APPROVE.match(l):
                        nxt = "\n".join(lines[i + 1:i + 6])
                        if ACTION.search(nxt):
                            _emit(hits, rel, i + 1, l, f"{head[:50]} lets the model's own 'approved' field release/approve an item without a reviewer step")
                    elif PROMOTE.search(l):
                        cond = next((lines[j] for j in range(i - 1, max(a, i - 4) - 1, -1) if PROMOTE_COND.match(lines[j])), None)
                        if cond:
                            _emit(hits, rel, i + 1, l, f"{head[:50]} promotes an item to an approved state straight from an LLM conclusion ({snippet(cond, 80)})")
        else:
            for i, line in enumerate(lines):
                if MODEL_APPROVE_JS.match(line) and ACTION.search("\n".join(lines[i + 1:i + 5])):
                    _emit(hits, rel, i + 1, line, "model's own 'approved' field gates a release/approval action without a reviewer step")
    # de-duplicate (same file+line)
    seen, out = set(), []
    for h in hits:
        if (h.path, h.line) not in seen:
            seen.add((h.path, h.line))
            out.append(h)
    return out[:40]
