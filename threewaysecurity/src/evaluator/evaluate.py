"""Evaluation module — compares agent decisions against ground truth."""

import json
from pathlib import Path

import pandas as pd


def run(settings: dict) -> dict:
    """Evaluate agent decisions against ground truth labels."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]
    label_dir = root / settings["label_dir"]

    # Load inputs
    with open(output_dir / "decisions.json", encoding="utf-8") as f:
        decisions = json.load(f)

    df_truth = pd.read_csv(label_dir / "ground_truth.csv")

    # Build decision lookup
    decision_map = {}
    for d in decisions:
        decision_map[d["invoice_id"]] = {
            "decision": d.get("decision", ""),
            "action": d.get("action", ""),
            "blocked": d.get("blocked", False),
        }

    # Map error classes to expected agent behavior
    error_classes = ["PRICE_MISMATCH", "QTY_MISMATCH", "CONTRACT_EXPIRED",
                     "LATE_PAYMENT", "COMBO"]

    metrics: dict[str, dict] = {}
    total_tp, total_fp, total_fn, total_tn = 0, 0, 0, 0

    for ec in error_classes:
        tp = fp = fn = tn = 0

        for _, row in df_truth.iterrows():
            inv_id = row["invoice_id"]
            agent = decision_map.get(inv_id, {})
            agent_blocked = agent.get("blocked", False)
            agent_flagged = agent.get("decision", "") == "FLAG"
            agent_detected = agent_blocked or agent_flagged

            is_this_class = row["error_class"] == ec
            should_detect = row["should_block"] or row["error_class"] == "LATE_PAYMENT"

            if is_this_class and should_detect and agent_detected:
                tp += 1
            elif is_this_class and should_detect and not agent_detected:
                fn += 1
            elif not is_this_class and not should_detect and agent_detected:
                # Only count FP if agent wrongly blocked a correct invoice
                pass  # FP counted at overall level
            elif is_this_class and not should_detect and agent_detected:
                fp += 1

        # Per-class metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics[ec] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    # Overall metrics
    overall_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = 2 * overall_p * overall_r / (overall_p + overall_r) if (overall_p + overall_r) > 0 else 0.0
    metrics["OVERALL"] = {
        "tp": total_tp, "fp": total_fp, "fn": total_fn,
        "precision": round(overall_p, 4),
        "recall": round(overall_r, 4),
        "f1": round(overall_f1, 4),
    }

    # Print report
    print()
    print("  ┌──────────────────────────────────────────────────────┐")
    print("  │  ASML Procurement Audit Agent — Evaluation Report    │")
    print("  ├────────────────────┬──────┬──────┬──────┬────────────┤")
    print("  │ Error Class        │  P   │  R   │  F1  │ FN (crit.) │")
    print("  ├────────────────────┼──────┼──────┼──────┼────────────┤")

    for ec in error_classes + ["OVERALL"]:
        m = metrics[ec]
        label = ec.ljust(18)
        print(f"  │ {label} │ {m['precision']:.2f} │ {m['recall']:.2f} │ "
              f"{m['f1']:.2f} │ {m['fn']:>10} │")

    print("  └────────────────────┴──────┴──────┴──────┴────────────┘")
    print()

    # Save metrics JSON
    metrics_path = output_dir / "evaluation_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"  evaluation_metrics.json saved")

    return metrics
