"""
Vergelijkt twee RCM-uitvoerbestanden (rcm_output.json) en toont per risico wat er
verandert: final residual risk, rating en control-betrouwbaarheid. Nieuwe of
verdwenen risico's (bijvoorbeeld extra UC6-risico's of nieuwe fraudescenario's)
worden apart gemeld.

Risico's worden gekoppeld op hun bronreferenties (F-2024-03, FS-02, ...) en niet op
RISK-id, zodat de vergelijking ook klopt als de nummering verschuift na een
wijziging in de invoer.

Gebruik:
  python demo/compare_runs.py demo/outputs/basis/rcm_output.json demo/outputs/whatif/rcm_output.json
  python demo/compare_runs.py <run_a.json> <run_b.json> --out-md demo/outputs/vergelijking.md
  python demo/compare_runs.py <a> <b> --all      (toon ook risico's zonder verschil)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def key_of(risk: dict) -> str:
    stage1 = risk.get("stage1", {})
    refs = stage1.get("source_references", [])
    if stage1.get("uc6_generated"):
        return "UC6<" + " + ".join(refs[:-1]) + ">"
    return " + ".join(refs) if refs else risk.get("risk_id", "?")


def short_rel(assessments: list[dict]) -> str:
    mapping = {"Reliable": "R", "Partially Reliable": "P", "Unreliable": "U", "Not Assessed": "NA"}
    return "/".join(mapping.get(a.get("control_reliability", ""), "?") for a in assessments)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vergelijk twee RCM-runs per risico.")
    parser.add_argument("run_a")
    parser.add_argument("run_b")
    parser.add_argument("--out-md", help="Schrijf de tabel ook naar dit Markdown-bestand")
    parser.add_argument("--all", action="store_true", help="Toon ook risico's zonder verschil")
    args = parser.parse_args()

    a = {key_of(r): r for r in load(args.run_a).get("risks", [])}
    b = {key_of(r): r for r in load(args.run_b).get("risks", [])}

    lines = [
        "| Risico (bronreferenties) | ID A | ID B | Final A | Final B | Verschil | Rating A -> B | Betrouwbaarheid A -> B |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    changed = 0
    for key in a:
        if key not in b:
            continue
        ra, rb = a[key], b[key]
        fa = ra["stage3"]["final_residual_risk"]
        fb = rb["stage3"]["final_residual_risk"]
        rel_a = short_rel(ra["stage3"]["controls_it_assessment"])
        rel_b = short_rel(rb["stage3"]["controls_it_assessment"])
        differs = fa != fb or rel_a != rel_b
        if differs:
            changed += 1
        if differs or args.all:
            lines.append(
                f"| {key} | {ra['risk_id']} | {rb['risk_id']} | {fa} | {fb} | {round(fb - fa, 2):+} "
                f"| {ra['stage3']['final_residual_rating']} -> {rb['stage3']['final_residual_rating']} | {rel_a} -> {rel_b} |"
            )

    only_a = [k for k in a if k not in b]
    only_b = [k for k in b if k not in a]

    header = [
        f"Run A: {args.run_a} ({len(a)} risico's)",
        f"Run B: {args.run_b} ({len(b)} risico's)",
        f"Gewijzigd: {changed} | alleen in A: {len(only_a)} | alleen in B: {len(only_b)}",
        "Legenda betrouwbaarheid: R = Reliable, P = Partially Reliable, U = Unreliable, NA = Not Assessed",
        "",
    ]
    footer = []
    if only_a:
        footer += ["", "Alleen in run A:"] + [f"- {k}" for k in only_a]
    if only_b:
        footer += ["", "Alleen in run B:"] + [f"- {k}" for k in only_b]

    text = "\n".join(header + lines + footer)
    print(text)
    if args.out_md:
        Path(args.out_md).write_text(text + "\n", encoding="utf-8")
        print(f"\nGeschreven naar {args.out_md}")


if __name__ == "__main__":
    main()
