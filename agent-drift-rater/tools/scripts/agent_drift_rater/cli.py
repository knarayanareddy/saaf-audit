"""Command-line interface for the Agent Drift Rater.

Run from the repo root:
    python -m tools.scripts.agent_drift_rater.cli selftest
    python -m tools.scripts.agent_drift_rater.cli rate --simulate
    python -m tools.scripts.agent_drift_rater.cli rate --path <local repo> --no-llm
    python -m tools.scripts.agent_drift_rater.cli rate --repo APM-Writer
    python -m tools.scripts.agent_drift_rater.cli report --run <run_id>
    python -m tools.scripts.agent_drift_rater.cli publish --run <run_id> [--dry-run]
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config, issues, mandate as mandate_mod, outputs, pipeline
from .inventory import Unit, build_inventory, load_overrides
from .judge import ClaudeJudge, MockJudge
from .run_log import RunLog, new_run_id
from .schema_check import validate_findings
from .sources import GitHubSource, LocalSource, GhError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("agent_drift_rater")


# --------------------------------------------------------------------------- source wiring

def _make_source(args) -> Any:
    if args.simulate:
        return LocalSource.fixtures(config.FIXTURE_ORG_FILE, config.FIXTURE_REPOS_DIR)
    if getattr(args, "path", None):
        return LocalSource.single(Path(args.path))
    return GitHubSource(config.ORG, config.CACHE_DIR, offline=getattr(args, "offline", False),
                        refresh=getattr(args, "refresh", False))


def _make_judge(args, run_log) -> Optional[Any]:
    if getattr(args, "no_llm", False):
        return None
    if args.simulate:
        return MockJudge()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set — running deterministic only (--no-llm).")
        return None
    return ClaudeJudge(getattr(args, "model", None) or config.DEFAULT_MODEL, run_log)


def _mandates_dir(args) -> Path:
    return config.FIXTURE_MANDATES_DIR if args.simulate else config.MANDATES_DIR


def _collect_units(source, args, overrides) -> List:
    repos = source.list_repos()
    if getattr(args, "repo", None):
        wanted = set(args.repo)
        repos = [r for r in repos if r.name in wanted]
    units = []
    for repo in repos:
        inv = build_inventory(source, repo, overrides)
        for unit in inv.units:
            units.append(unit)
    return units


# --------------------------------------------------------------------------- commands

def cmd_rate(args) -> int:
    source = _make_source(args)
    overrides = load_overrides()
    mode = "sim" if args.simulate else ("local" if getattr(args, "path", None) else "org")
    run_log = RunLog(new_run_id(mode))
    run_log.event("run_start", mode=mode, source=source.kind)
    judge = _make_judge(args, run_log)
    mandates_dir = _mandates_dir(args)

    units = _collect_units(source, args, overrides)
    if not units:
        logger.error("No agent units found.")
        return 2

    unit_reports: List[Dict[str, Any]] = []
    all_findings: List[Dict[str, Any]] = []
    for unit in units:
        m_path = mandates_dir / f"{unit.unit_id}.json"
        mandate = mandate_mod.load(m_path)
        if mandate is None:
            source_files = {p: t for p, t in unit.files.items()
                            if p.lower().endswith((".md", ".txt", ".prompt"))}
            mandate = mandate_mod.extract_deterministic(
                unit.unit_id, unit.repo.name, unit.root, unit.repo.head_sha, source_files or unit.files)
        rating, findings, advice = pipeline.rate_unit(
            unit, mandate, judge, run_log, truncated=unit.repo.truncated)
        all_findings.extend(findings)
        unit_reports.append(pipeline.unit_report(unit, rating, findings, advice))

    all_findings = outputs.assign_ids(all_findings)
    # distribute ids back into unit reports
    cursor = 0
    for ur in unit_reports:
        n = len(ur["findings"])
        ur["findings"] = all_findings[cursor:cursor + n]
        cursor += n

    report = {
        "schema": "agent-drift-rater/report-v1",
        "run": {
            "run_id": run_log.run_id, "org": source.org,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine": "deterministic + Claude pass" if judge else "deterministic only",
            "tool_commit": _git_head(),
        },
        "units": unit_reports,
    }
    run_log.write_json("report.json", report)
    run_log.write_json("findings-flat.json", all_findings)
    run_log.write_text("scorecard.md", outputs.render_scorecard(report))
    run_log.write_text("dashboard.html", outputs.render_dashboard(report))

    errors = validate_findings(all_findings)
    if errors:
        logger.error("Findings FAILED schema validation:\n%s", "\n".join(errors[:10]))
        run_log.event("schema_invalid", count=len(errors))
    else:
        run_log.event("schema_valid", findings=len(all_findings))

    logger.info("Run %s: %d unit(s), %d finding(s). Artifacts in %s",
                run_log.run_id, len(unit_reports), len(all_findings), run_log.dir)
    for ur in unit_reports:
        logger.info("  %-40s %-13s (controls %s, conf %s)", ur["unit_id"],
                    ur["ratings"]["residual"], ur["ratings"]["control_strength"],
                    ur["ratings"]["confidence"])
    print(run_log.dir)
    return 0 if not errors else 3


def cmd_extract_mandates(args) -> int:
    source = _make_source(args)
    overrides = load_overrides()
    mandates_dir = _mandates_dir(args)
    units = _collect_units(source, args, overrides)
    for unit in units:
        source_files = {p: t for p, t in unit.files.items()
                        if p.lower().endswith((".md", ".txt", ".prompt"))}
        fresh = mandate_mod.extract_deterministic(
            unit.unit_id, unit.repo.name, unit.root, unit.repo.head_sha, source_files or unit.files)
        existing = mandate_mod.load(mandates_dir / f"{unit.unit_id}.json")
        if existing and existing.status == "confirmed" and not args.force:
            final = mandate_mod.reconcile(existing, fresh)
        else:
            final = fresh
        mandate_mod.save(final, mandates_dir)
        logger.info("  %-40s status=%s rules=%d", unit.unit_id, final.status, len(final.hard_rules))
    logger.info("Mandates written to %s — review and run confirm-mandate.", mandates_dir)
    return 0


def cmd_confirm_mandate(args) -> int:
    mandates_dir = _mandates_dir(args)
    path = mandates_dir / f"{args.unit}.json"
    mandate = mandate_mod.load(path)
    if mandate is None:
        logger.error("No mandate for unit '%s' at %s", args.unit, path)
        return 2
    mandate_mod.confirm(mandate, args.reviewer, args.notes or "", date.today().isoformat())
    mandate_mod.save(mandate, mandates_dir)
    logger.info("Confirmed mandate for %s (reviewer: %s)", args.unit, args.reviewer)
    return 0


def cmd_report(args) -> int:
    run_dir = config.RUNS_DIR / args.run if args.run else _latest_run()
    if not run_dir or not (run_dir / "report.json").exists():
        logger.error("No run found. Run `rate` first.")
        return 2
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    (run_dir / "scorecard.md").write_text(outputs.render_scorecard(report), encoding="utf-8")
    (run_dir / "dashboard.html").write_text(outputs.render_dashboard(report), encoding="utf-8")
    logger.info("Rendered scorecard.md and dashboard.html in %s", run_dir)
    print(run_dir)
    return 0


def cmd_publish(args) -> int:
    run_dir = config.RUNS_DIR / args.run if args.run else _latest_run()
    if not run_dir or not (run_dir / "report.json").exists():
        logger.error("No run found.")
        return 2
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    provisional = [u["unit_id"] for u in report["units"] if u["provisional"]]
    if provisional and not args.allow_provisional:
        logger.error("Refusing to publish: %d unit(s) are provisional (unconfirmed mandate). "
                     "Confirm mandates or pass --allow-provisional.\n  %s",
                     len(provisional), ", ".join(provisional))
        return 4
    # Leak check: committed text must not contain source code.
    committed = [outputs.render_scorecard(report), json.dumps(report["units"])]
    source_files = _gather_source(report)
    leaks = outputs.check_no_verbatim(committed, source_files) if source_files else []
    if leaks:
        logger.error("Leak check FAILED — committed output overlaps source code:\n%s",
                     "\n".join(leaks[:5]))
        return 4
    if args.dry_run:
        logger.info("Dry run OK: %d units, no provisional blockers, leak check passed.",
                    len(report["units"]))
        return 0
    dest = config.PUBLISH_DIR / date.today().isoformat()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "findings.json").write_text(
        json.dumps(json.loads((run_dir / "findings-flat.json").read_text()), indent=2), encoding="utf-8")
    (dest / "scorecard.md").write_text(outputs.render_scorecard(report), encoding="utf-8")
    (dest / "dashboard.html").write_text(outputs.render_dashboard(report), encoding="utf-8")
    logger.info("Published to %s", dest)
    print(dest)
    return 0


def cmd_create_issues(args) -> int:
    """Turn approved fix suggestions into GitHub issues in the analyzed repos (dry-run default)."""
    run_dir = config.RUNS_DIR / args.run if args.run else _latest_run()
    if not run_dir or not (run_dir / "report.json").exists():
        logger.error("No run found. Run `rate` first.")
        return 2
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    org = report["run"]["org"]

    if args.approved:
        raw = json.loads(Path(args.approved).read_text(encoding="utf-8"))
        fix_ids = issues.parse_approved(raw)
        source = f"approved set ({args.approved})"
    else:
        # No approvals file: default to every suggestion on High-residual agents.
        fix_ids = [f"{u['unit_id']}__{i}" for u in report["units"] if u["ratings"]["residual"] == "High"
                   for i in range(len(u.get("advice") or []))]
        source = "all suggestions on High-rated agents (no --approved file given)"

    drafts = issues.drafts_for(report, fix_ids)
    if args.repo:
        allow = set(args.repo)
        drafts = [d for d in drafts if d.repo in allow]
    if not drafts:
        logger.info("No issues to create from %s.", source)
        return 0

    by_repo: Dict[str, List[issues.IssueDraft]] = {}
    for d in drafts:
        by_repo.setdefault(d.repo, []).append(d)

    logger.info("%d issue(s) across %d repo(s) from %s.", len(drafts), len(by_repo), source)
    if not args.yes:
        print(f"\n=== DRY RUN — no issues created. {len(drafts)} issue(s) would be filed ===\n")
        for repo, ds in sorted(by_repo.items()):
            print(f"## {org}/{repo}  ({len(ds)} issue(s))")
            for d in ds:
                print(f"\n  TITLE: {d.title}")
                for line in d.body.splitlines():
                    print(f"  | {line}")
            print()
        print("To create them for real: re-run with --yes and --repo <name> for each repo to allow.")
        return 0

    if not args.repo:
        logger.error("Refusing to create issues without an explicit --repo whitelist. "
                     "Add --repo <name> for each repo you intend to post to.")
        return 4
    created = 0
    for repo, ds in sorted(by_repo.items()):
        existing = issues.existing_titles(org, repo)
        for d in ds:
            if d.title in existing:
                logger.info("skip (exists): %s/%s — %s", org, repo, d.title)
                continue
            url = issues.create_issue(org, d, label=args.label)
            if url:
                created += 1
                logger.info("created: %s", url)
                print(url)
    logger.info("Created %d issue(s).", created)
    return 0


def cmd_selftest(args) -> int:
    from . import selftest
    return selftest.run()


# --------------------------------------------------------------------------- helpers

def _latest_run() -> Optional[Path]:
    if not config.RUNS_DIR.exists():
        return None
    runs = sorted((p for p in config.RUNS_DIR.iterdir() if p.is_dir()), key=lambda p: p.name)
    return runs[-1] if runs else None


def _git_head() -> str:
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=config.REPO_ROOT,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "n/a"
    except Exception:  # noqa: BLE001
        return "n/a"


def _gather_source(report: Dict[str, Any]) -> Dict[str, str]:
    """Best-effort: read source from the blob cache for a real leak check (empty for fixtures)."""
    return {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent_drift_rater",
                                     description="Static drift-susceptibility rating for SAAF agents.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("--simulate", action="store_true", help="Use synthetic fixtures (offline).")
        p.add_argument("--path", help="Rate a single local repository directory.")
        p.add_argument("--repo", action="append", help="Limit to this org repo (repeatable).")
        p.add_argument("--no-llm", action="store_true", help="Deterministic checks only.")
        p.add_argument("--offline", action="store_true", help="Use cache only; never call gh.")
        p.add_argument("--refresh", action="store_true", help="Ignore cache and refetch.")
        p.add_argument("--model", help="Claude model id for the judge.")

    p_rate = sub.add_parser("rate", help="Fetch, extract mandates, and rate.")
    add_common(p_rate)
    p_rate.set_defaults(func=cmd_rate)

    p_ext = sub.add_parser("extract-mandates", help="Stage 1: write editable mandate files.")
    add_common(p_ext)
    p_ext.add_argument("--force", action="store_true", help="Overwrite confirmed mandates.")
    p_ext.set_defaults(func=cmd_extract_mandates)

    p_conf = sub.add_parser("confirm-mandate", help="Mark a unit's mandate confirmed.")
    p_conf.add_argument("--unit", required=True)
    p_conf.add_argument("--reviewer", required=True)
    p_conf.add_argument("--notes")
    p_conf.add_argument("--simulate", action="store_true")
    p_conf.set_defaults(func=cmd_confirm_mandate)

    p_rep = sub.add_parser("report", help="Re-render scorecard and dashboard for a run.")
    p_rep.add_argument("--run")
    p_rep.set_defaults(func=cmd_report)

    p_pub = sub.add_parser("publish", help="Leak-check and copy a run to agent-drift-review/.")
    p_pub.add_argument("--run")
    p_pub.add_argument("--dry-run", action="store_true")
    p_pub.add_argument("--allow-provisional", action="store_true")
    p_pub.set_defaults(func=cmd_publish)

    p_iss = sub.add_parser("create-issues",
                           help="File approved fix suggestions as GitHub issues (dry-run default).")
    p_iss.add_argument("--run", help="Run id (default: most recent).")
    p_iss.add_argument("--approved", help="JSON file of approved fix ids (from the dashboard).")
    p_iss.add_argument("--repo", action="append", help="Whitelist a repo to post to (repeatable).")
    p_iss.add_argument("--yes", action="store_true", help="Actually create issues (needs --repo).")
    p_iss.add_argument("--label", action="store_true",
                       help="Add the 'agent-drift' label (must already exist in the repo).")
    p_iss.set_defaults(func=cmd_create_issues)

    p_self = sub.add_parser("selftest", help="Run offline fixtures and assertions.")
    p_self.set_defaults(func=cmd_selftest)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except GhError as exc:
        logger.error("GitHub access error: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
