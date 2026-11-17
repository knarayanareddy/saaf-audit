"""SAAF-014: third-party code is pulled in by a floating reference (unpinned or floor-only dependencies without a
lockfile, CDN scripts without Subresource Integrity, curl|bash, pip install from a git branch, actions on a branch).
Origin: weakness class observed across SAAF repositories (SAAF Security Challenge, Nov 2026)."""
import os
import re
from _lib import Hit, snippet

CHECK = {
    "id": "SAAF-014",
    "slug": "unpinned-dependencies-and-cdn",
    "category": "supply-chain-untrusted-component",
    "severity": "Low",
    "title": "Third-party code is loaded from an unpinned source (floating dependency versions with no lockfile, CDN "
             "script without Subresource Integrity, or a mutable branch reference)",
    "intended": "Every third-party component (Python/npm package, browser script, CI action, installer script) is fetched "
                "in an exact, reviewed version, backed by a lockfile with hashes or a Subresource Integrity (SRI) hash.",
    "actual": "Dependencies are declared without a version or with a floor/range only (>=, ~=, ^, ~, *) and the project has "
              "no lockfile, or a <script>/<link> tag loads a CDN file without an integrity= attribute, or code is "
              "fetched from a moving reference (curl | bash, pip install git+...@main, uses: owner/repo@main).",
    "impact": "Every build, deployment or page load can silently receive different code. A compromised or malicious "
              "release of a dependency, or a compromised CDN, then executes in the audit agent's backend (with its API "
              "keys and auditee data) or in the reviewer's browser session. Builds are also not reproducible, which "
              "weakens audit evidence about which code produced a result.",
    "recommendation": "Commit a lockfile with hashes (uv.lock / poetry.lock / pip-compile --generate-hashes, "
                      "package-lock.json with npm ci) and install with it in CI; pin direct dependencies to exact "
                      "versions; self-host browser libraries or add an exact version plus integrity=\"sha384-...\" "
                      "crossorigin=\"anonymous\"; pin installers, git installs and actions to a release tag or full commit "
                      "SHA and verify a checksum instead of piping curl into a shell; enable Dependabot/Renovate for updates.",
    "refs": "CWE-1357, CWE-829, CWE-494, OWASP LLM03",
}

LOCKS_PY = {"poetry.lock", "uv.lock", "pdm.lock", "pipfile.lock", "requirements.lock", "requirements.txt.lock",
            "pylock.toml", "constraints.txt"}
LOCKS_JS = {"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock"}
SKIP_PATH = re.compile(r"(^|/)(sample_data|samples?|testdata|mocks?|demo_data)(/|$)", re.I)

REQ_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")
PINNED_EQ = re.compile(r"(?<![=!<>~])===?\s*[0-9][^,;\s*]*$")


def _dirs_up(rel):
    parts = rel.split("/")[:-1]
    for n in range(len(parts), -1, -1):
        yield "/".join(parts[:n])


def _has_lock(repo, rel, locks):
    """Lockfile in the same directory or any ancestor (checked on disk: big lockfiles are skipped by repo.files)."""
    for d in _dirs_up(rel):
        try:
            names = {n.lower() for n in os.listdir(repo.root / d if d else repo.root)}
        except OSError:
            continue
        if names & locks:
            return True
    return False


# ---------------------------------------------------------------- python / npm manifests
def _py_unpinned(spec):
    """True when a requirement string is not an exact pin."""
    spec = spec.split(";")[0].strip()
    if not spec or not REQ_NAME.match(spec):
        return False
    if "@" in spec and re.search(r"@\s*(git\+)?https?://", spec):       # direct URL
        return not re.search(r"@[0-9a-f]{40}\b|/[0-9a-f]{40}\b", spec)
    rest = REQ_NAME.sub("", spec, count=1)
    rest = re.sub(r"^\[[^\]]*\]", "", rest).strip()
    return not PINNED_EQ.search(rest)


def _check_requirements(repo, rel, hits):
    total = unp = 0
    first = None
    for i, raw in enumerate(repo.lines(rel), 1):
        line = raw.split(" #")[0].strip()
        if not line or line.startswith("#"):
            continue
        if "--hash" in line or line.startswith(("-c ", "--constraint")):
            return                                        # hash-pinned or constrained file
        if line.startswith("-") or line.startswith(("http://", "https://")):
            continue
        if line.startswith("git+"):
            total += 1
            if not re.search(r"@[0-9a-f]{40}\b|@v?\d+\.\d+", line):
                unp += 1; first = first or (i, line)
            continue
        total += 1
        if _py_unpinned(line):
            unp += 1; first = first or (i, line)
    if total and unp and unp * 2 >= total and not _has_lock(repo, rel, LOCKS_PY):
        hits.append(Hit(rel, first[0], snippet(first[1]),
                        f"{unp} of {total} requirements are unpinned or floor-only and no lockfile/hashes exist"))


def _toml_dep_strings(text):
    m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if not m:
        return []
    start = text[:m.start()].count("\n") + 1
    out = []
    for s in re.finditer(r"[\"']([^\"']+)[\"']", m.group(1)):
        out.append((start + m.group(1)[:s.start()].count("\n"), s.group(1)))
    return out


def _check_pyproject(repo, rel, hits):
    d = rel.rsplit("/", 1)[0] if "/" in rel else ""
    try:
        sib = os.listdir(repo.root / d if d else repo.root)
    except OSError:
        sib = []
    if any(re.match(r"requirements.*\.txt$", n, re.I) for n in sib):
        return                                              # covered by the requirements file check
    text = repo.read(rel)
    deps = _toml_dep_strings(text)
    unp = [(n, s) for n, s in deps if _py_unpinned(s)]
    if deps and unp and len(unp) * 2 >= len(deps) and not _has_lock(repo, rel, LOCKS_PY):
        hits.append(Hit(rel, unp[0][0], snippet(unp[0][1]),
                        f"{len(unp)} of {len(deps)} dependencies are floor-only/unpinned and no lockfile exists"))


def _check_package_json(repo, rel, hits):
    text = repo.read(rel)
    total = unp = 0
    first = None
    for sec in ("dependencies", "devDependencies"):
        m = re.search(r'"%s"\s*:\s*\{(.*?)\}' % sec, text, re.S)
        if not m:
            continue
        for e in re.finditer(r'"([^"]+)"\s*:\s*"([^"]*)"', m.group(1)):
            total += 1
            v = e.group(2).strip()
            floating = (v in ("", "*", "latest", "x") or v[0] in "^~<>" or re.search(r"\.x\b|\|\|", v) or
                        (re.match(r"(git|https?)[+:]", v) and not re.search(r"#[0-9a-f]{40}$|#v?\d", v)))
            if floating:
                unp += 1
                if first is None:
                    first = text[:m.start(1) + e.start()].count("\n") + 1, f'"{e.group(1)}": "{v}"'
    if total and unp and unp * 4 >= total * 3 and not _has_lock(repo, rel, LOCKS_JS):  # mostly floating
        hits.append(Hit(rel, first[0], snippet(first[1]),
                        f"{unp} of {total} npm dependencies use ^/~/*/latest ranges and no lockfile exists"))


# ---------------------------------------------------------------- CDN scripts without SRI
CDN_HOSTS = (r"cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com|cdn\.tailwindcss\.com|code\.jquery\.com|"
             r"ajax\.googleapis\.com|stackpath\.bootstrapcdn\.com|maxcdn\.bootstrapcdn\.com|cdn\.bootcss\.com|"
             r"esm\.sh|cdn\.skypack\.dev|cdn\.plot\.ly|d3js\.org|cdn\.datatables\.net|cdn\.socket\.io")
CDN_TAG = re.compile(r"<(?:script|link)\b[^>]*?\b(?:src|href)\s*=\s*[\"'](https?://(?:%s)[^\"']*)[\"'][^>]*>" % CDN_HOSTS,
                     re.I | re.S)
CDN_QUICK = re.compile(CDN_HOSTS)
EXACT_VER = re.compile(r"@\d+\.\d+\.\d+|/\d+\.\d+\.\d+/|[?&]v=\d|-\d+\.\d+\.\d+(\.min)?\.(js|css)")


def _check_cdn(repo, hits):
    for rel in repo.files({".html", ".htm", ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".j2", ".jinja"}):
        if SKIP_PATH.search(rel) or rel.endswith((".min.js", ".bundle.js")):
            continue
        text = repo.read(rel)
        if not CDN_QUICK.search(text):
            continue
        for m in CDN_TAG.finditer(text):
            tag = m.group(0)
            if re.search(r"\bintegrity\s*=", tag, re.I):
                continue
            if re.search(r"rel\s*=\s*[\"'](preconnect|dns-prefetch|icon)", tag, re.I):
                continue
            url = m.group(1)
            ln = text[:m.start()].count("\n") + 1
            ver = "exact version in URL but no SRI hash" if EXACT_VER.search(url) else "no exact version and no SRI hash"
            hits.append(Hit(rel, ln, snippet(url), f"CDN resource loaded without integrity= ({ver})"))


# ---------------------------------------------------------------- curl|bash, git installs, mutable refs in docs/CI
CMD_EXTS = {".md", ".sh", ".bash", ".yml", ".yaml", ".mk"}
CMD_NAMES = {"dockerfile", "makefile"}
PIPE_SH = re.compile(r"\b(?:curl|wget)\b[^|\n]*\|\s*(?:sudo\s+(?:-\S+\s+)*)?(?:ba|z|da)?sh\b|"
                     r"\b(?:curl|wget)\b[^|\n]*\|\s*(?:sudo\s+)?python3?\b|"
                     r"\b(?:ba|z)?sh\s+-c\s+[\"']?\$\(\s*(?:curl|wget)\b|\b(?:ba)?sh\s+<\(\s*(?:curl|wget)\b", re.I)
PIP_GIT = re.compile(r"\bpip3?\s+install\b[^\n]*?git\+https?://[^\s\"'@]+(?:@([\w./-]+))?", re.I)
RAW_MAIN = re.compile(r"raw\.githubusercontent\.com/[\w.-]+/[\w.-]+/(?:refs/heads/)?(main|master|HEAD|develop)/", re.I)
FETCH_CMD = re.compile(r"\b(curl|wget|pip3?\s+install|bash|sh|python3?)\b", re.I)
USES_BRANCH = re.compile(r"^\s*-?\s*uses:\s*(?!\./)([\w.-]+/[\w./-]+)@(main|master|HEAD|develop|latest)\b")
USES_TAG = re.compile(r"^\s*-?\s*uses:?\s+(?!\./)([\w.-]+/[\w./-]+)@([\w.-]+)\s*(?:#.*)?$")
FIRST_PARTY_OWNERS = {"actions", "github"}
SHA_REF = re.compile(r"^[0-9a-f]{40}$")
GIT_CLONE = re.compile(r"\bgit\s+clone\b(?P<args>[^\n]*?)https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?")


def _check_commands(repo, hits):
    for rel in repo.files(CMD_EXTS, CMD_NAMES):
        if SKIP_PATH.search(rel):
            continue
        is_ci = rel.endswith((".yml", ".yaml"))
        lines = repo.lines(rel)
        for i, line in enumerate(lines):
            if PIPE_SH.search(line):
                hits.append(Hit(rel, i + 1, snippet(line), "remote script piped straight into a shell/interpreter"))
                continue
            m = PIP_GIT.search(line)
            if m and (not m.group(1) or m.group(1).lower() in ("main", "master", "head", "develop", "dev")):
                hits.append(Hit(rel, i + 1, snippet(line), "pip install from a git URL without a pinned tag/commit"))
                continue
            if RAW_MAIN.search(line) and FETCH_CMD.search(line):
                hits.append(Hit(rel, i + 1, snippet(line),
                                "file downloaded from a branch (main/master) of a raw GitHub URL, not a pinned commit"))
                continue
            m = USES_BRANCH.match(line) if (is_ci or rel.endswith(".md")) else None
            if m:
                hits.append(Hit(rel, i + 1, snippet(line), "action/reusable workflow referenced by a branch, not a tag or SHA"))
                continue
            if is_ci:
                m = USES_TAG.match(line)
                if m and m.group(1).split("/")[0].lower() not in FIRST_PARTY_OWNERS and not SHA_REF.match(m.group(2)) \
                        and ".github/workflows" in rel:
                    hits.append(Hit(rel, i + 1, snippet(line), "third-party action pinned to a mutable tag, not a full commit SHA "
                                                              "(a tag can be re-pointed by the action owner)"))
                    continue
                m = GIT_CLONE.search(line)
                if m and "-b " not in m.group("args") and "--branch" not in m.group("args") \
                        and "github.repository" not in line:
                    window = "\n".join(lines[i:i + 6])
                    if not re.search(r"\bcheckout\b|reset\s+--hard|--branch|\bgit\s+-C\b[^\n]*\bfetch\b", window):
                        hits.append(Hit(rel, i + 1, snippet(line),
                                        "repository cloned in CI at its default branch HEAD and executed, no pinned ref"))


def run(repo):
    hits = []
    list(repo.files(None, {"\0"}))                          # primes repo._cache["all"] (every non-skipped file)
    for rel in repo._cache["all"]:
        base = rel.rsplit("/", 1)[-1].lower()
        if SKIP_PATH.search(rel):
            continue
        if re.match(r"requirements[\w.-]*\.txt$", base) and base not in LOCKS_PY \
                and not re.search(r"dev|test|lint|docs?\b|ci\b", base):      # tooling-only files are not shipped code
            _check_requirements(repo, rel, hits)
        elif base == "pyproject.toml":
            _check_pyproject(repo, rel, hits)
        elif base == "package.json":
            _check_package_json(repo, rel, hits)
    _check_cdn(repo, hits)
    _check_commands(repo, hits)
    return hits
