#!/usr/bin/env python3
"""
Customs: a contribution check for shared SAAF prompts, skills and agent settings.

Customs inspects text that AI agents will read as instructions and blocks
content that could turn an agent against the person running it: hidden text,
override language, routes for sending data out, reaching for credentials, and
switched off approvals.

It uses no AI model and makes no network calls, so it gives the same result
for every organisation, whichever AI tool they use, and it runs offline.

Examples
  python3 customs/customs.py                        scan the whole repository
  python3 customs/customs.py --changed-since main   scan only what a branch changes
  python3 customs/customs.py skills/my-skill        scan a file or folder

Exit codes: 0 cleared, 1 blocked, 2 could not run.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import fnmatch
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        sys.exit("Customs needs Python 3.11 or later, or the 'tomli' package.")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules as R  # noqa: E402

VERSION = "0.1.0"
CONFIG_FILE = "customs.toml"
ALLOWLIST_FILE = ".customs-allowlist.toml"
PRUNE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".customs-tool"}
CONTROL_FILES = (CONFIG_FILE, ALLOWLIST_FILE, ".github/CODEOWNERS")
CONTROL_FOLDERS = ("customs/", ".github/workflows/")
REQUIRED_EXCEPTION_FIELDS = ("rule", "path", "justification", "approved_by", "expires")

DEFAULT_CONFIG = {
    # Files an agent is likely to read as instructions or configuration.
    "include": [
        "**/*.md",
        "**/*.mdc",
        "**/*.prompt",
        "**/*.prompt.yml",
        "**/*.txt",
        "**/.cursorrules",
        "**/.windsurfrules",
        "**/*mcp*.json",
        "**/.claude/*.json",
        "**/.vscode/*.json",
        "**/*agent*.json",
        "**/*agent*.yml",
        "**/*agent*.yaml",
        "**/*agent*.toml",
    ],
    "exclude": [
        ".git/**",
        "node_modules/**",
        ".venv/**",
        "venv/**",
        "customs/**",
        ".customs-tool/**",
        "tests/fixtures/**",
    ],
    # Destinations a shared skill may point to without being reported.
    # Subdomains are included, so github.com also covers docs.github.com.
    "allowed_domains": [
        "github.com",
        "githubusercontent.com",
        "saafproject.com",
        "saaf-portal.vercel.app",
        "europa.eu",
        "norea.nl",
        "isaca.org",
        "isaca.nl",
        "iia.nl",
        "nba.nl",
        "forhumanity.center",
        "python.org",
        "pypi.org",
        "microsoft.com",
    ],
    "fail_on": "High",
}


@dataclass
class Finding:
    rule: str
    severity: str
    title: str
    file: str
    line: int
    excerpt: str
    reason: str
    raw: str = ""
    accepted: bool = False
    justification: str = ""


def rank(severity: str) -> int:
    return R.SEVERITIES.index(severity)


# Git and control files

def git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args],
            cwd=root, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout


def read_control_file(root: Path, name: str, base_ref: str | None) -> str | None:
    """Read Customs settings or exceptions.

    When checking a contribution these are read from the base branch, so a
    contribution cannot loosen the rules or approve its own exceptions.
    """
    if base_ref:
        return git(root, "show", f"{base_ref}:{name}")
    path = root / name
    return path.read_text(encoding="utf-8") if path.is_file() else None


def load_config(root: Path, base_ref: str | None, config_path: str | None = None) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if config_path:
        text = Path(config_path).read_text(encoding="utf-8")
    else:
        text = read_control_file(root, CONFIG_FILE, base_ref)
    if text:
        data = tomllib.loads(text)
        for key in ("include", "exclude", "allowed_domains", "fail_on"):
            if key in data:
                config[key] = data[key]
        for key in ("include", "exclude", "allowed_domains"):
            config[key] = list(config[key]) + list(data.get(f"extra_{key}", []))
    if config["fail_on"] not in R.SEVERITIES:
        raise ValueError(f"fail_on must be one of: {', '.join(R.SEVERITIES)}")
    return config


def load_exceptions(root: Path, base_ref: str | None, warnings: list[str]) -> list[dict]:
    text = read_control_file(root, ALLOWLIST_FILE, base_ref)
    if not text:
        return []
    valid = []
    for number, entry in enumerate(tomllib.loads(text).get("exception", []), start=1):
        missing = [f for f in REQUIRED_EXCEPTION_FIELDS if not str(entry.get(f, "")).strip()]
        if missing:
            warnings.append(f"Exception {number} ignored: missing {', '.join(missing)}.")
            continue
        expires = entry["expires"]
        if isinstance(expires, datetime):
            expires = expires.date()
        elif isinstance(expires, str):
            try:
                expires = date.fromisoformat(expires)
            except ValueError:
                warnings.append(f"Exception {number} ignored: expires must be a date (YYYY-MM-DD).")
                continue
        if expires < date.today():
            warnings.append(
                f"Exception {number} ({entry['rule']} in {entry['path']}) expired on "
                f"{expires.isoformat()} and was not applied."
            )
            continue
        valid.append(dict(entry, expires=expires))
    return valid


def apply_exceptions(findings: list[Finding], exceptions: list[dict]) -> None:
    for finding in findings:
        for entry in exceptions:
            if (
                entry["rule"] == finding.rule
                and matches(finding.file, entry["path"])
                and (not entry.get("contains") or entry["contains"] in finding.raw)
            ):
                finding.accepted = True
                finding.justification = (
                    f"{entry['justification']} (approved by {entry['approved_by']}, "
                    f"expires {entry['expires'].isoformat()})"
                )
                break


# Choosing files

def matches(rel: str, pattern: str) -> bool:
    return fnmatch.fnmatch(rel, pattern) or (
        pattern.startswith("**/") and fnmatch.fnmatch(rel, pattern[3:])
    )


def selected(rel: str, config: dict) -> bool:
    return any(matches(rel, p) for p in config["include"]) and not any(
        matches(rel, p) for p in config["exclude"]
    )


def walk(base: Path):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        raise RuntimeError(f"'{path}' is outside the repository root {root}.") from None


def collect_files(root: Path, config: dict, targets: list[str], base_ref: str | None):
    """Return (files to scan, every path the contribution changed)."""
    if base_ref:
        out = git(root, "diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...HEAD")
        if out is None:
            raise RuntimeError(
                f"could not compare with '{base_ref}'. Check that the branch exists and "
                "that the checkout includes full history (fetch-depth: 0)."
            )
        changed = [line.strip() for line in out.splitlines() if line.strip()]
        return [rel for rel in changed if selected(rel, config)], changed

    files: set[str] = set()
    for target in targets or [str(root)]:
        path = Path(target).resolve()
        if path.is_file():
            files.add(relative(path, root))  # a file named explicitly is always scanned
        elif path.is_dir():
            files.update(r for r in (relative(p, root) for p in walk(path)) if selected(r, config))
        else:
            raise RuntimeError(f"'{target}' does not exist.")
    return sorted(files), []


# Checks

def shorten(text: str, width: int = 120) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def visible(text: str) -> str:
    """Show invisible characters so a reviewer can see them in the report."""
    out, tags = [], 0
    for char in text:
        code = ord(char)
        if 0xE0000 <= code <= 0xE007F:
            tags += 1
            continue
        if tags:
            out.append(f"[{tags} hidden tag characters]")
            tags = 0
        out.append(f"[U+{code:04X}]" if char in R.HIDDEN_CHARACTERS else char)
    if tags:
        out.append(f"[{tags} hidden tag characters]")
    return "".join(out)


def excerpt(text: str, match: re.Match | None = None, context: str | None = None,
            width: int = 120) -> str:
    if match is None:
        snippet = shorten(visible(text.strip()), width)
    elif len(text) > width:
        start = max(0, match.start() - 30)
        snippet = text[start:start + width]
        snippet = ("..." if start else "") + snippet + ("..." if start + width < len(text) else "")
        snippet = visible(snippet.strip())
    else:
        snippet = visible(text.strip())
    return f"[{context}] {snippet}" if context else snippet


def negated(text: str, start: int) -> bool:
    clause = re.split(r"[.;:!?]", text[:start])[-1][-40:]
    return bool(R.NEGATION.search(clause)) and not R.NOT_A_NEGATION.search(clause)


def domain_allowed(host: str, config: dict) -> bool:
    host = host.lower()
    return any(host == d or host.endswith("." + d) for d in config["allowed_domains"])


def destination_allowed(text: str, match: re.Match, config: dict) -> bool:
    if "dest" not in match.re.groupindex or match.group("dest") is None:
        return False
    tail = text[match.start("dest"):]
    url = R.URL.match(tail)
    if url:
        return domain_allowed(host_of(url), config)
    email = R.EMAIL.match(tail)
    return bool(email) and domain_allowed(email.group("domain"), config)


def host_of(url_match: re.Match) -> str:
    return url_match.group("host").lower().rsplit("@", 1)[-1].split(":")[0].rstrip(".")


def check_patterns(rel, number, text, config, context=None) -> list[Finding]:
    findings = []
    for rule in R.LINE_RULES:
        for pattern in rule["patterns"]:
            hit = None
            for m in pattern.finditer(text):
                if rule.get("negation_guard") and negated(text, m.start()):
                    continue
                if destination_allowed(text, m, config):
                    continue
                hit = m
                break
            if hit:
                findings.append(Finding(
                    rule["id"], rule["severity"], rule["title"], rel, number,
                    excerpt(text, hit, context), rule["reason"], raw=text,
                ))
                break
    return findings


def check_destinations(rel, number, text, config, context=None) -> list[Finding]:
    findings, seen = [], set()
    for m in R.URL.finditer(text):
        host = host_of(m)
        if host in seen or domain_allowed(host, config):
            continue
        seen.add(host)
        findings.append(Finding(
            "CUS-N2", "Medium", "Unapproved web address", rel, number, excerpt(text, m, context),
            f"Points to '{host}', which is not on the approved domain list. An agent "
            "following this file could send data there or fetch new instructions from it. "
            "If the address is legitimate, add it to allowed_domains in customs.toml.",
            raw=text,
        ))
    for m in R.EMAIL.finditer(text):
        domain = m.group("domain").lower()
        if domain in seen or domain_allowed(domain, config):
            continue
        seen.add(domain)
        findings.append(Finding(
            "CUS-N3", "Low", "Unapproved email address", rel, number, excerpt(text, m, context),
            f"Names an email address at '{domain}', which is not on the approved domain "
            "list. Check why a shared skill needs it.",
            raw=text,
        ))
    return findings


def is_emoji_join(line: str, index: int) -> bool:
    """A zero width joiner between two emoji is normal (for example in 👩‍💻)."""
    def pictographic(i: int) -> bool:
        if i < 0 or i >= len(line):
            return False
        code = ord(line[i])
        return code >= 0x1F000 or 0x2600 <= code <= 0x27BF or code == 0xFE0F
    return pictographic(index - 1) and pictographic(index + 1)


def check_hidden_characters(rel, number, line, config, first_line) -> list[Finding]:
    found, smuggled = [], []
    for index, char in enumerate(line):
        code = ord(char)
        if 0xE0000 <= code <= 0xE007F:
            found.append("tag characters")
            if 0xE0020 <= code <= 0xE007E:
                smuggled.append(chr(code - 0xE0000))
        elif char == "\ufeff" and first_line and index == 0:
            continue
        elif char == "\u200d" and is_emoji_join(line, index):
            continue
        elif char in R.HIDDEN_CHARACTERS:
            found.append(R.HIDDEN_CHARACTERS[char])
    if not found:
        return []
    reason = (
        f"{len(found)} invisible character(s) ({', '.join(sorted(set(found)))}). "
        "Invisible characters can hide instructions from a human reviewer while an "
        "AI agent still reads them."
    )
    message = "".join(smuggled).strip()
    if message:
        reason += f' The hidden text reads: "{shorten(message, 120)}".'
    findings = [Finding("CUS-H1", "High", "Invisible characters", rel, number,
                        excerpt(line), reason, raw=line)]
    if message:
        findings += check_patterns(rel, number, message, config, context="hidden text")
        findings += check_destinations(rel, number, message, config, context="hidden text")
    return findings


def decode_base64(blob: str) -> str | None:
    try:
        data = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=True)
        return data.decode("utf-8")
    except (binascii.Error, ValueError):
        return None


def readable(text: str) -> bool:
    if len(text) < 20 or " " not in text:
        return False
    printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
    return printable / len(text) >= 0.9


def check_encoded(rel, number, line, config) -> list[Finding]:
    findings = []
    for m in R.ENCODED.finditer(line):
        blob = m.group(0)
        if re.fullmatch(r"[0-9a-fA-F]+", blob):
            continue  # hashes and similar identifiers
        decoded = decode_base64(blob)
        if decoded is not None and readable(decoded):
            findings.append(Finding(
                "CUS-H3", "High", "Encoded instructions", rel, number, excerpt(line, m),
                f'A long encoded string decodes to readable text: "{shorten(decoded, 120)}". '
                "Encoding is a common way to slip instructions past a reviewer.",
                raw=line,
            ))
            findings += check_patterns(rel, number, decoded, config, context="decoded")
            findings += check_destinations(rel, number, decoded, config, context="decoded")
        else:
            findings.append(Finding(
                "CUS-H3", "Low", "Long encoded string", rel, number, excerpt(line, m),
                "A long encoded string could not be read as text. Confirm what it is "
                "before merging.",
                raw=line,
            ))
    return findings


def check_comments(rel, text, config, existing) -> list[Finding]:
    findings = []
    for m in R.HTML_COMMENT.finditer(text):
        body = " ".join(m.group(1).split())
        if not body:
            continue
        start = text.count("\n", 0, m.start()) + 1
        end = text.count("\n", 0, m.end()) + 1
        findings.append(Finding(
            "CUS-H2", "Medium", "Hidden comment", rel, start, shorten(visible(body), 120),
            "Text inside an HTML comment is invisible when the file is viewed on GitHub, "
            "but an agent reading the raw file sees it. Move genuine notes outside the "
            "comment or remove them.",
            raw=m.group(0),
        ))
        if end > start:  # phrases split across lines inside the comment
            already = {f.rule for f in existing if start <= f.line <= end}
            findings += [f for f in check_patterns(rel, start, body, config, context="comment")
                         if f.rule not in already]
    return findings


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen, out = set(), []
    for f in findings:
        key = (f.rule, f.file, f.line, f.excerpt)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def scan_text(rel: str, text: str, config: dict) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        findings += check_hidden_characters(rel, number, line, config, first_line=number == 1)
        findings += check_patterns(rel, number, line, config)
        findings += check_destinations(rel, number, line, config)
        findings += check_encoded(rel, number, line, config)
    findings += check_comments(rel, text, config, findings)
    return dedupe(findings)


def control_changes(changed: list[str]) -> list[Finding]:
    return [
        Finding(
            "CUS-G1", "Medium", "Changes Customs controls", rel, 0, "",
            "This contribution changes Customs itself, its settings, its exception list "
            "or a CI workflow. Changes like these only take effect after merge and should "
            "be approved by a code owner.",
        )
        for rel in changed
        if rel in CONTROL_FILES or rel.startswith(CONTROL_FOLDERS)
    ]


# Reporting

def print_report(findings, files, config, warnings, blocking) -> None:
    print(f"Customs {VERSION}: inspected {len(files)} file(s), "
          f"blocking at {config['fail_on']} and above.\n")
    wrap = dict(width=92, initial_indent=" " * 11, subsequent_indent=" " * 11)
    current = None
    for f in (f for f in findings if not f.accepted):
        if f.file != current:
            current = f.file
            print(f.file)
        where = f"line {f.line}" if f.line else "file"
        flag = "BLOCK" if id(f) in blocking else "note "
        print(f"  {flag}  {where:<9} {f.severity:<7} {f.rule}  {f.title}")
        if f.excerpt:
            print(textwrap.fill("> " + f.excerpt, **wrap))
        print(textwrap.fill(f.reason, **wrap))
    accepted = [f for f in findings if f.accepted]
    if accepted:
        print("\nAccepted exceptions")
        for f in accepted:
            print(f"  {f.rule}  {f.file}:{f.line}  {f.justification}")
    if warnings:
        print("\nWarnings")
        for w in warnings:
            print(f"  {w}")
    others = sum(1 for f in findings if not f.accepted) - len(blocking)
    if blocking:
        print(f"\nResult: BLOCKED. {len(blocking)} finding(s) at {config['fail_on']} or above "
              f"must be fixed or approved as an exception. {others} other finding(s) for review.")
    else:
        print(f"\nResult: CLEARED. {others} finding(s) below {config['fail_on']} for review, "
              f"{len(accepted)} accepted exception(s).")


def md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("<", "&lt;").replace("\n", " ")


def markdown_report(findings, files, config, warnings, blocking) -> str:
    status = "Blocked" if blocking else "Cleared"
    lines = [
        f"## Customs: {status}", "",
        f"Inspected {len(files)} file(s). Findings at **{config['fail_on']}** or above block the merge.", "",
    ]
    open_findings = [f for f in findings if not f.accepted]
    if open_findings:
        lines += ["| | Severity | Rule | Location | What Customs found | Why it matters |",
                  "|---|---|---|---|---|---|"]
        for f in open_findings:
            mark = "🛑" if id(f) in blocking else "⚠️"
            where = f"`{f.file}`" + (f" line {f.line}" if f.line else "")
            lines.append(f"| {mark} | {f.severity} | {f.rule} | {where} | "
                         f"{md_cell(f.excerpt or f.title)} | {md_cell(f.reason)} |")
    accepted = [f for f in findings if f.accepted]
    if accepted:
        lines += ["", "### Accepted exceptions", ""]
        lines += [f"- {f.rule} in `{f.file}` line {f.line}: {md_cell(f.justification)}" for f in accepted]
    if warnings:
        lines += ["", "### Warnings", ""] + [f"- {md_cell(w)}" for w in warnings]
    return "\n".join(lines) + "\n"


def _escape_data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(text: str) -> str:
    return _escape_data(text).replace(":", "%3A").replace(",", "%2C")


def annotate(findings, blocking) -> None:
    """Print GitHub annotations so findings appear on the pull request lines."""
    for f in findings:
        if f.accepted:
            continue
        if id(f) in blocking:
            level = "error"
        elif rank(f.severity) >= rank("Medium"):
            level = "warning"
        else:
            level = "notice"
        message = f"{f.reason} Found: {f.excerpt}" if f.excerpt else f.reason
        print(f"::{level} file={_escape_property(f.file)},line={max(f.line, 1)},"
              f"title={_escape_property(f.rule + ' ' + f.title)}::{_escape_data(message)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="customs",
        description="Inspect shared prompts, skills and agent settings before they are merged.",
    )
    parser.add_argument("targets", nargs="*", help="files or folders to scan (default: whole repository)")
    parser.add_argument("--root", default=".", help="repository root (default: current folder)")
    parser.add_argument("--changed-since", metavar="REF",
                        help="only scan files changed since this branch or commit, for example origin/main")
    parser.add_argument("--config", help="use this settings file instead of customs.toml")
    parser.add_argument("--fail-on", choices=R.SEVERITIES, help="lowest severity that blocks (default: High)")
    parser.add_argument("--json", metavar="FILE", help="also write results as JSON")
    parser.add_argument("--markdown", metavar="FILE", help="also write a Markdown summary")
    parser.add_argument("--allow-empty", action="store_true",
                        help="clear a full scan that matches no files (default: report NOT ASSESSED, exit 2)")
    parser.add_argument("--version", action="version", version=f"Customs {VERSION}")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    warnings: list[str] = []
    try:
        config = load_config(root, args.changed_since, args.config)
        if args.fail_on:
            config["fail_on"] = args.fail_on
        files, changed = collect_files(root, config, args.targets, args.changed_since)
        exceptions = load_exceptions(root, args.changed_since, warnings)
    except (RuntimeError, ValueError, OSError, tomllib.TOMLDecodeError) as error:
        print(f"Customs could not run: {error}", file=sys.stderr)
        return 2

    # No silent pass: a scan that inspected nothing has not cleared anything.
    # A pull request that changes no inspected files (--changed-since) is fine.
    if not files and not args.changed_since and not args.allow_empty:
        what = ", ".join(args.targets) if args.targets else "the repository"
        print(f"Customs {VERSION}: NOT ASSESSED. No files in {what} matched the include "
              "patterns (or all were excluded), so nothing was inspected. Check include and "
              "exclude in customs.toml, or pass --allow-empty if this is expected.", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except UnicodeDecodeError:
            findings.append(Finding(
                "CUS-X1", "Low", "Unreadable file", rel, 0, "",
                "The file is not valid UTF-8 text, so Customs could not inspect it. "
                "Confirm that no agent reads it, or convert it.",
            ))
            continue
        findings += scan_text(rel, text, config)
    findings += control_changes(changed)
    apply_exceptions(findings, exceptions)
    findings.sort(key=lambda f: (f.file, f.line, -rank(f.severity), f.rule))

    threshold = rank(config["fail_on"])
    blocking = {id(f) for f in findings if not f.accepted and rank(f.severity) >= threshold}

    print_report(findings, files, config, warnings, blocking)
    summary = markdown_report(findings, files, config, warnings, blocking)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        annotate(findings, blocking)
        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary:
            with open(step_summary, "a", encoding="utf-8") as handle:
                handle.write(summary)
    if args.markdown:
        Path(args.markdown).write_text(summary, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "tool": "Customs",
            "version": VERSION,
            "result": "blocked" if blocking else "cleared",
            "fail_on": config["fail_on"],
            "files_scanned": files,
            "findings": [{k: v for k, v in asdict(f).items() if k != "raw"} for f in findings],
            "warnings": warnings,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
