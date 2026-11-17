import csv, hashlib, os, subprocess, sys
from pathlib import Path
from conftest import SCANNER


def run(scanner, repo, metrics=None, overrides=None):
    r = scanner.scan(repo, metrics)
    for k, v in (overrides or {}).items():
        (r["severity"] if k in scanner.FLAGS else r["strength"])[k] = v
    return r, scanner.score(r["severity"], r["strength"])


def write_metrics(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["period", "case_type", "cases", "escalations"]); w.writerows(rows)
    return path


# ---- discrimination -------------------------------------------------------

def test_risky_repo_scores_critical(scanner, risky_repo, tmp_path):
    m = write_metrics(tmp_path / "m.csv", [["Q1", "pay", 800, 80], ["Q1", "vendor", 200, 30],
                                           ["Q3", "pay", 790, 40], ["Q3", "vendor", 210, 12]])
    r, (s, band, _, _) = run(scanner, risky_repo, str(m))
    assert s >= 9 and band == "Critical"
    for f in ("RF1", "RF3", "RF4", "RF5", "RF6"):
        assert r["severity"][f] == 1.0, f


def test_controlled_repo_scores_low(scanner, controlled_repo):
    r, (s, band, _, _) = run(scanner, controlled_repo)
    assert s < 3 and band == "Low"
    assert all(v == 1.0 for v in r["strength"].values())


# ---- individual red flags --------------------------------------------------

def test_rf1_detects_prompt_write(scanner, risky_repo):
    r, _ = run(scanner, risky_repo)
    assert any("agent.py" in e for e in r["evidence"]["RF1"])


def test_rf5_detects_required_to_plausible_in_history(scanner, risky_repo):
    r, _ = run(scanner, risky_repo)
    assert any("required" in e and "plausible" in e for e in r["evidence"]["RF5"])


def test_rf4_stable_mix_drop_is_warning(scanner, controlled_repo, tmp_path):
    m = write_metrics(tmp_path / "m.csv", [["Q1", "a", 500, 50], ["Q1", "b", 500, 50],
                                           ["Q2", "a", 500, 20], ["Q2", "b", 500, 20]])
    r, (s, _, _, floors) = run(scanner, controlled_repo, str(m))
    assert r["severity"]["RF4"] == 1.0
    assert s >= 6 and any("escalations falling" in f for f in floors)


def test_rf4_drop_with_shifted_mix_is_partial(scanner, controlled_repo, tmp_path):
    m = write_metrics(tmp_path / "m.csv", [["Q1", "hard", 800, 160], ["Q1", "easy", 200, 2],
                                           ["Q2", "hard", 200, 40], ["Q2", "easy", 800, 8]])
    r, _ = run(scanner, controlled_repo, str(m))
    assert r["severity"]["RF4"] == 0.5


def test_rf4_without_metrics_or_monitoring_is_not_testable(scanner, risky_repo):
    r, _ = run(scanner, risky_repo)
    assert r["severity"]["RF4"] == 0.5
    assert any("NOT TESTABLE" in e for e in r["evidence"]["RF4"])


# ---- scoring rules (C1 for our own rubric) --------------------------------

def zero(scanner):
    return {f: 0.0 for f in scanner.FLAGS}, {c: 0.0 for c in scanner.CONTROLS}


def test_score_bounds(scanner):
    sev, st = zero(scanner)
    assert scanner.score(sev, st)[0] == 1.0
    sev = {f: 1.0 for f in sev}
    assert scanner.score(sev, st)[0] == 10.0


def test_controls_never_remove_more_than_60_percent(scanner):
    sev, st = zero(scanner)
    sev["RF2"] = 1.0; st = {c: 1.0 for c in st}
    _, _, residual, _ = scanner.score(sev, st)
    assert residual["RF2"] >= 0.4 * scanner.FLAGS["RF2"][1] - 1e-9


def test_floor_self_edit_without_versioning_and_rollback(scanner):
    sev, st = zero(scanner); sev["RF1"] = 1.0
    assert scanner.score(sev, st)[0] >= 7.0


def test_floor_prompt_only_rules(scanner):
    sev, st = zero(scanner); sev["RF3"] = 1.0
    assert scanner.score(sev, st)[0] >= 6.0


def test_floor_no_replayable_log(scanner):
    sev, st = zero(scanner); sev["RF6"] = 1.0
    assert scanner.score(sev, st)[0] >= 5.0


def test_overrides_are_applied_via_cli(risky_repo, tmp_path):
    ov = tmp_path / "ov.json"; ov.write_text('{"RF1": 0.0}')
    out = tmp_path / "o.json"
    subprocess.run([sys.executable, str(SCANNER), str(risky_repo), "--overrides", str(ov), "--json-out", str(out)], check=True)
    import json
    d = json.loads(out.read_text())
    assert d["severity"]["RF1"] == 0.0 and d["overrides"] == {"RF1": 0.0}


# ---- the scanner itself must be read-only ---------------------------------

def tree_hash(root):
    h = hashlib.sha256()
    for dp, dns, fns in sorted(os.walk(root)):
        dns.sort()
        for fn in sorted(fns):
            p = Path(dp) / fn
            h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def test_scanner_does_not_modify_target(risky_repo, tmp_path):
    before = tree_hash(risky_repo)
    subprocess.run([sys.executable, str(SCANNER), str(risky_repo),
                    "--json-out", str(tmp_path / "o.json"), "--md-out", str(tmp_path / "o.md")], check=True)
    assert tree_hash(risky_repo) == before
