import argparse
import concurrent.futures
import os
from datetime import date
from pathlib import Path

from agents.llm import BACKENDS, DEFAULT_BACKEND, ENV_VAR, get_backend
from agents.orchestrator import build_vendor_profile, determine_frameworks
from agents.security_agent import run_security_agent
from agents.resilience_agent import run_resilience_agent
from agents.gov_baseline_agent import run_gov_baseline_agent
from agents.ai_trust_agent import run_ai_trust_agent
from agents.document_validity_agent import run_document_validity_agent
from synthesizer.synthesizer import aggregate_findings, compute_rag_scorecard
from synthesizer.scorecard import write_scorecard, write_gap_register
from synthesizer.memo import write_audit_memo
from synthesizer.google_output import write_scorecard_csv, write_gap_register_csv, write_audit_memo_html
from utils.document_parser import parse_documents
from models.finding import REVIEW_FLAG, Finding

OUTPUT_FILES = ("scorecard.xlsx", "gap_register.xlsx", "audit_memo.docx",
                "scorecard.csv", "gap_register.csv", "audit_memo.html")

AGENT_MAP = {
    "security": run_security_agent,
    "resilience": run_resilience_agent,
    "gov_baseline": run_gov_baseline_agent,
    "ai_trust": run_ai_trust_agent,
}


def _no_progress(stage: str, status: str, **data) -> None:
    pass


def run_pipeline(
    questionnaire_path: Path,
    doc_paths: list[Path],
    output_dir: Path,
    progress=_no_progress,
) -> dict:
    """Run the full audit. `progress(stage, status, **data)` is called as each
    stage starts ("running") and ends ("done" / "error"), e.g. for a UI."""
    output_dir.mkdir(parents=True, exist_ok=True)

    all_paths = [questionnaire_path] + list(doc_paths)
    progress("documents", "running", count=len(all_paths))
    vendor_docs = parse_documents(all_paths)
    progress("documents", "done", count=len(all_paths), names=[Path(p).name for p in all_paths])

    print("Extracting vendor profile...")
    progress("profile", "running")
    profile = build_vendor_profile(vendor_docs)
    print(f"Vendor: {profile.name} | Sector: {profile.sector} | AI system: {profile.is_ai_system}")
    progress("profile", "done", vendor=profile.name, sector=profile.sector,
             is_ai_system=profile.is_ai_system, is_dutch_government_vendor=profile.is_dutch_government_vendor)

    agents_to_run = determine_frameworks(profile)
    print(f"Running agents: {agents_to_run}")
    progress("routing", "done", agents=agents_to_run + ["document_validity"],
             skipped=[name for name in AGENT_MAP if name not in agents_to_run])

    today = date.today()
    all_findings: list[Finding] = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(AGENT_MAP[name], vendor_docs): name
            for name in agents_to_run
        }
        futures[executor.submit(run_document_validity_agent, vendor_docs, today)] = "document_validity"
        for name in futures.values():
            progress(name, "running")
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                findings = future.result()
            except Exception as exc:
                progress(name, "error", error=str(exc))
                raise
            print(f"  {name}: {len(findings)} findings")
            progress(name, "done", findings=len(findings),
                     gaps=sum(f.status == "Gap" for f in findings))
            all_findings.extend(findings)

    all_findings = aggregate_findings(all_findings)
    scorecard = compute_rag_scorecard(all_findings)
    progress("scorecard", "done", scorecard=scorecard, findings=len(all_findings),
             review_flags=sum(REVIEW_FLAG in f.evidence for f in all_findings))

    print("Writing outputs...")

    # Draft memo text once, reuse for both DOCX and HTML
    progress("memo", "running")
    memo_text = write_audit_memo(profile, all_findings, scorecard, output_dir / "audit_memo.docx")
    progress("memo", "done")
    progress("outputs", "running")

    # Excel (Microsoft Office)
    write_scorecard(scorecard, output_dir / "scorecard.xlsx")
    write_gap_register(all_findings, output_dir / "gap_register.xlsx")

    # Google Workspace (CSV + HTML)
    write_scorecard_csv(scorecard, output_dir / "scorecard.csv")
    write_gap_register_csv(all_findings, output_dir / "gap_register.csv")
    write_audit_memo_html(profile, all_findings, scorecard, memo_text, output_dir / "audit_memo.html")

    print(f"\nDone. Outputs written to {output_dir}/")
    print("\n  Microsoft Office:")
    print("    scorecard.xlsx, gap_register.xlsx, audit_memo.docx")
    print("  Google Workspace (drag & drop into Google Drive):")
    print("    scorecard.csv, gap_register.csv, audit_memo.html")
    print()
    for fw, data in scorecard.items():
        print(f"  {fw}: {data['rag']}")
    progress("outputs", "done", files=[name for name in OUTPUT_FILES])

    return {
        "scorecard_xlsx": output_dir / "scorecard.xlsx",
        "gap_register_xlsx": output_dir / "gap_register.xlsx",
        "memo_docx": output_dir / "audit_memo.docx",
        "scorecard_csv": output_dir / "scorecard.csv",
        "gap_register_csv": output_dir / "gap_register.csv",
        "memo_html": output_dir / "audit_memo.html",
    }


def main():
    parser = argparse.ArgumentParser(description="SAAF Vendor Risk Audit Agent")
    parser.add_argument("--questionnaire", required=True, type=Path,
                        help="Path to vendor questionnaire (PDF/DOCX/XLSX/TXT)")
    parser.add_argument("--docs", nargs="*", default=[], type=Path,
                        help="Additional vendor documents (SOC2, ISO cert, etc.)")
    parser.add_argument("--output-dir", default=Path("output"), type=Path,
                        help="Directory for output files (default: ./output)")
    parser.add_argument("--backend", choices=BACKENDS, default=None,
                        help="Model backend: 'api' (ANTHROPIC_API_KEY) or 'claude-code' "
                             "(Claude Agent SDK, using your own Claude Code login). "
                             f"Default: ${ENV_VAR} or '{DEFAULT_BACKEND}'")
    args = parser.parse_args()

    if args.backend:
        os.environ[ENV_VAR] = args.backend
    print(f"Backend: {get_backend()}")

    run_pipeline(
        questionnaire_path=args.questionnaire,
        doc_paths=args.docs,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
