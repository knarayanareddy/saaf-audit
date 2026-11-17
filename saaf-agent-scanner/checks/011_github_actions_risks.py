"""SAAF-011: GitHub Actions workflow weaknesses (pwn-request checkout, script injection, over-broad token on PR
triggers, third-party actions / reusable workflows / cloned code pinned to a mutable ref).
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import re
from _lib import Hit, snippet, redact

CHECK = {
    "id": "SAAF-011",
    "slug": "github-actions-risks",
    "category": "ci-cd-workflow-injection",
    "severity": "Medium",
    "title": "GitHub Actions workflow runs untrusted input or unpinned third-party code with a privileged token",
    "intended": "CI workflows only run reviewed, version-pinned code, treat pull-request and issue text as data, and give "
                "the GITHUB_TOKEN and secrets to jobs that do not execute attacker-influenced code.",
    "actual": "A workflow does at least one of: checks out pull-request head code under pull_request_target/workflow_run "
              "(which carry secrets and a write token); interpolates attacker-controlled ${{ github.event.* }} / "
              "${{ github.head_ref }} values directly into a run:/script: body; grants contents: write (or write-all) "
              "to jobs that run on pull requests; or references third-party actions, reusable workflows or cloned "
              "repositories by a mutable tag/branch (@v1, @main, git clone HEAD) instead of a full commit SHA. "
              "Each location is tagged [High]/[Medium]/[Low] in the detail; mutable-ref hits are the lowest "
              "severity unless the job holds a write token.",
    "impact": "A pull-request author can run code with repository secrets and a write token (pwn request), or inject "
              "shell commands through a branch name, PR title or issue body. A moved tag or compromised upstream "
              "action/workflow/repo executes inside the job with its token and can tamper with releases, commits "
              "and downstream consumers of the reusable workflow.",
    "recommendation": "Never check out PR head code under pull_request_target/workflow_run; use pull_request, or split an "
                      "unprivileged build from a privileged follow-up that only consumes artifacts as data. Pass "
                      "event values via env: and quote \"$VAR\" in the script. Set workflow-level `permissions: "
                      "contents: read` and grant write only to the single job that needs it, gated to trusted refs "
                      "(and a protected environment for secrets). Pin every third-party action, reusable workflow "
                      "and cloned dependency to a full 40-character commit SHA (with a version comment) and let "
                      "Dependabot/Renovate update them.",
    "refs": "CWE-1357, CWE-78, CWE-829, OWASP LLM03 (supply chain)",
}

WF = re.compile(r"(^|/)\.github/workflows/[^/]+\.ya?ml$", re.I)
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*[\"']?([^\s\"'#]+)")
SHA = re.compile(r"^[0-9a-f]{40}$", re.I)
BRANCHY = re.compile(r"^(main|master|HEAD|develop|dev|trunk|latest|release)$", re.I)
EXPR = re.compile(r"\$\{\{(.*?)\}\}", re.S)
TAINT = re.compile(
    r"github\.head_ref\b|"
    r"github\.event\.(?:issue|pull_request|comment|review|review_comment|discussion|head_commit|pages|workflow_run|"
    r"release|client_payload)\b[\w.\[\]*'\"-]*?\.(?:title|body|ref|label|message|email|head_branch|display_title|"
    r"branch)\b|"
    r"github\.event\.(?:head_commit|commits)[\w.\[\]*]*\.(?:message|author\.(?:name|email))\b|"
    r"github\.event\.pages[\w.\[\]*]*\.page_name\b|"
    r"github\.event\.(?:pull_request|workflow_run)\.head\.(?:ref|label)\b|"
    r"github\.event\.(?:pull_request|workflow_run)\.head_(?:ref|branch)\b")
BASE_REF = re.compile(r"\.base\.ref\b|\.base_ref\b|\.repo\.")  # writer-only names: not exploitable (see finding -06)
PR_HEAD = re.compile(
    r"github\.event\.pull_request\.head\.(?:sha|ref|repo)|github\.head_ref|github\.event\.workflow_run\.head_|"
    r"refs/pull/[^\s'\"]*/(?:head|merge)|github\.event\.pull_request\.merge_commit_sha|"
    r"github\.event\.(?:issue|comment)\.[\w.]*pull_request")
PR_CHECKOUT_RUN = re.compile(r"gh\s+pr\s+checkout|git\s+(?:fetch|checkout|pull|switch)\b[^\n]*"
                             r"(?:head_ref|pull_request\.head|refs/pull/|workflow_run\.head)")
PRIV_TRIGGER = {"pull_request_target", "workflow_run", "issue_comment", "issues", "pull_request_review",
                "pull_request_review_comment", "discussion", "discussion_comment"}
PR_TRIGGER = {"pull_request", "pull_request_target"}
SENSITIVE_WRITE = {"contents", "packages", "actions", "deployments"}
GIT_CLONE = re.compile(r"git\s+clone\b[^\n]*https?://(?:www\.)?github\.com/[\w.-]+/[\w.-]+")
CLONE_PIN = re.compile(r"--branch\b|\s-b\s|git\s+(?:-C\s+\S+\s+)?checkout\s+[0-9a-f]{40}|git\s+reset\s+--hard\s+[0-9a-f]{40}")
RAW_MUTABLE = re.compile(r"(?:curl|wget)\b[^\n]*(?:raw\.githubusercontent\.com|github\.com)/[^\s'\"]*/(?:main|master|HEAD)/")
DOC_REUSABLE = re.compile(r"uses:\s*[\w.-]+/[\w.-]+/\.github/workflows/[\w./-]+@(?:main|master|HEAD|develop|trunk)\b")


def _strip(line: str) -> str:
    return re.sub(r"(^|\s)#.*$", "", line).rstrip()


def _indent(l: str) -> int:
    return len(l) - len(l.lstrip())


def _triggers(lines):
    for i, l in enumerate(lines):
        m = re.match(r"^[\"']?on[\"']?:\s*(.*)$", l)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest:
            return set(re.findall(r"[a-z_]+", rest))
        out, child = set(), None
        for l2 in lines[i + 1:]:
            if not l2.strip():
                continue
            if _indent(l2) == 0:
                break
            child = _indent(l2) if child is None else child
            if _indent(l2) == child:
                mm = re.match(r"^\s*-?\s*([a-z_]+)", l2)
                if mm:
                    out.add(mm.group(1))
        return out
    return set()


def _perms(lines, i):
    """Return (set of write scopes incl. 'write-all') for a permissions: key at index i."""
    m = re.match(r"^(\s*)permissions:\s*(.*)$", lines[i])
    rest, base = m.group(2).strip(), len(m.group(1))
    out = set()
    if rest:
        if rest == "write-all":
            out.add("write-all")
        out |= {k for k, v in re.findall(r"([\w-]+)\s*:\s*(write)", rest)}
        return out
    for l in lines[i + 1:]:
        if not l.strip():
            continue
        if _indent(l) <= base:
            break
        mm = re.match(r"^\s*([\w-]+):\s*write\b", l)
        if mm:
            out.add(mm.group(1))
    return out


def _jobs(lines):
    """[(name, start, end, key_indent)] for each job under the top-level jobs: key."""
    start = next((i for i, l in enumerate(lines) if re.match(r"^jobs:\s*$", l)), None)
    if start is None:
        return []
    jobs, child = [], None
    for i in range(start + 1, len(lines)):
        l = lines[i]
        if not l.strip():
            continue
        if _indent(l) == 0:
            break
        child = _indent(l) if child is None else child
        if _indent(l) == child and re.match(r"^\s*[\w-]+:\s*$", l):
            jobs.append([l.strip()[:-1], i, len(lines), child])
            if len(jobs) > 1:
                jobs[-2][2] = i
        elif _indent(l) < child:
            break
    if jobs:
        # trim last job at the end of the jobs block
        end = len(lines)
        for i in range(jobs[-1][1] + 1, len(lines)):
            if lines[i].strip() and _indent(lines[i]) == 0:
                end = i
                break
        jobs[-1][2] = end
    return [tuple(j) for j in jobs]


EXTRA_SECRET = re.compile(r"secrets\.(?!GITHUB_TOKEN\b)\w+")


def _guarded(lines, job):
    _, a, b, ki = job
    for l in lines[a + 1:b]:
        if l.strip() and _indent(l) == ki + 2 and (m := re.match(r"^\s*if:\s*(.*)$", l)) and \
                re.search(r"github\.event_name|github\.ref\b", m.group(1)):
            return True
    return False


def _run_bodies(lines):
    """Yield (line_idx, text) for each line of a run:/script: body (block scalars and inline)."""
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)(-\s+)?(run|script):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key_ind = len(m.group(1)) + (len(m.group(2)) if m.group(2) else 0)
        rest = m.group(4).strip()
        if rest[:1] in ("|", ">"):
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or _indent(lines[j]) > key_ind):
                if lines[j].strip():
                    yield j, lines[j]
                j += 1
            i = j
        else:
            if rest:
                yield i, rest
            i += 1


def _tainted_expr(text):
    for m in EXPR.finditer(text):
        e = m.group(1)
        if TAINT.search(e) and not BASE_REF.search(e):
            return e.strip()
    return None


def _scan_workflow(rel, raw):
    lines = [_strip(l) for l in raw.splitlines()]
    if not any(l.strip() for l in lines):
        return []
    trig = _triggers(lines)
    pr = bool(trig & PR_TRIGGER)
    priv = trig & PRIV_TRIGGER
    hits = []

    def add(rank, i, sev, why):
        hits.append((rank, Hit(rel, i + 1, redact(snippet(raw.splitlines()[i])), f"[{sev}] {why}")))

    # 1. pwn request: PR head code under privileged trigger
    if trig & {"pull_request_target", "workflow_run", "issue_comment"}:
        for i, l in enumerate(lines):
            if (re.match(r"^\s*(?:-\s+)?(ref|repository):", l) and PR_HEAD.search(l)) or \
                    (PR_CHECKOUT_RUN.search(l)):
                add(0, i, "High", f"checks out pull-request head code under {', '.join(sorted(trig & {'pull_request_target', 'workflow_run', 'issue_comment'}))} "
                                  "(runs attacker code with secrets/write token)")

    # 2. script injection
    for i, text in _run_bodies(lines):
        e = _tainted_expr(text)
        if e:
            sev = "High" if priv else "Medium"
            add(1 if priv else 2, i, sev, f"attacker-controlled ${{{{ {e[:60]} }}}} interpolated into a run/script body "
                                         "(shell/JS injection); pass it through env: instead")

    # 3. write token on PR triggers
    if pr:
        jobs = _jobs(lines)
        wf_perm = next((i for i, l in enumerate(lines) if re.match(r"^permissions:", l)), None)
        wf_set = _perms(lines, wf_perm) if wf_perm is not None else set()
        seen = set()
        for job in jobs:
            name, a, b, ki = job
            own = next((j for j in range(a + 1, b) if _indent(lines[j]) == ki + 2 and re.match(r"^\s*permissions:", lines[j])), None)
            src, scopes = (own, _perms(lines, own)) if own is not None else (wf_perm, wf_set)
            if src is None or src in seen or _guarded(lines, job):
                continue
            bad = {"write-all"} & scopes or (scopes if "pull_request_target" in trig else scopes & SENSITIVE_WRITE)
            if bad:
                seen.add(src)
                add(3, src, "Medium", f"write token ({', '.join(sorted(bad))}) available to job '{name}' that runs on "
                                      f"{', '.join(sorted(trig & PR_TRIGGER))}; PR-supplied code/tests can use it")
        if not jobs and wf_perm is not None:
            bad = {"write-all"} & wf_set or (wf_set if "pull_request_target" in trig else wf_set & SENSITIVE_WRITE)
            if bad:
                add(3, wf_perm, "Medium", f"write token ({', '.join(sorted(bad))}) granted on {', '.join(sorted(trig & PR_TRIGGER))}")

    # 4. mutable refs (needs job map for the first-party/write-token rule)
    jobs = _jobs(lines)
    wf_perm = next((i for i, l in enumerate(lines) if re.match(r"^permissions:", l)), None)
    wf_set = _perms(lines, wf_perm) if wf_perm is not None else set()

    def job_write(i, scopes_ok):
        for name, a, b, ki in jobs:
            if a <= i < b:
                own = next((j for j in range(a + 1, b) if _indent(lines[j]) == ki + 2 and re.match(r"^\s*permissions:", lines[j])), None)
                s = _perms(lines, own) if own is not None else wf_set
                return bool(s & scopes_ok)
        return bool(wf_set & scopes_ok)

    mutable_seen = {}
    for i, l in enumerate(lines):
        m = USES.match(l)
        if m:
            ref = m.group(1)
            if ref.startswith(("./", "docker://")) or "@" not in ref:
                continue
            target, _, ver = ref.rpartition("@")
            if SHA.match(ver) or "${{" in ref:
                continue
            first_party = target.lower().startswith(("actions/", "github/"))
            reusable = ".github/workflows/" in target
            sens = job_write(i, SENSITIVE_WRITE | {"write-all"})
            writes = sens or job_write(i, {"pull-requests", "issues"})
            if first_party and not (sens and (pr or EXTRA_SECRET.search(raw))):
                continue   # first-party tags: only noteworthy when the write job also runs on PRs or holds a non-default secret
            if (target, ver) in mutable_seen:   # one hit per action per workflow file
                mutable_seen[(target, ver)].append(i + 1)
                continue
            if reusable and BRANCHY.match(ver):
                add(4, i, "Medium", f"reusable workflow {target} pinned to branch '@{ver}': every caller runs whatever is on that branch")
            else:
                mutable_seen[(target, ver)] = []
                add(5, i, "Low" if not writes else "Medium",
                    f"{'first' if first_party else 'third'}-party {'reusable workflow' if reusable else 'action'} {target} pinned to mutable "
                    f"'@{ver}' instead of a commit SHA" + (" in a job holding a write token" if writes else ""))
    for i, text in _run_bodies(lines):
        if GIT_CLONE.search(text):
            body = "\n".join(t for j, t in _run_bodies(lines) if abs(j - i) <= 8)
            if not CLONE_PIN.search(body):
                add(5, i, "Low", "clones a GitHub repository at its default-branch HEAD (no commit/tag pin) and uses it in CI")
        elif RAW_MUTABLE.search(text):
            add(5, i, "Low", "downloads a script from a mutable branch URL (main/master/HEAD) inside the workflow")
    hits.sort(key=lambda t: (t[0], t[1].line))
    return [h for _, h in hits]


def run(repo):
    hits = []
    for rel in repo.files({".yml", ".yaml"}):
        if WF.search(rel):
            hits += _scan_workflow(rel, repo.read(rel))
    for rel in repo.files({".md"}):
        for i, l in enumerate(repo.lines(rel), 1):
            if DOC_REUSABLE.search(l):
                hits.append(Hit(rel, i, snippet(l), "[Low] documentation tells adopters to call a reusable workflow at "
                                                    "'@main' (mutable branch) instead of a commit SHA"))
    rank = {"High": 0, "Medium": 1, "Low": 2}
    hits.sort(key=lambda h: rank.get(h.detail[1:h.detail.index("]")], 3) if h.detail.startswith("[") else 3)
    return hits
