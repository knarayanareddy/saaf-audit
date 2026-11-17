"""Every check must fire on tests/fixtures/<ID>/vulnerable and stay silent on tests/fixtures/<ID>/safe.
Run: python3 -I -m pytest -q tests   (or: python3 -I tests/test_checks.py)"""
import sys, pathlib
TOOL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL))
import saaf_scan  # noqa: E402

FIX = TOOL / "tests" / "fixtures"
CHECKS = saaf_scan.load_checks()


def _hits(check_run, d):
    return check_run(saaf_scan.Repo(d, include_tests=True))


def test_every_check_has_fixtures():
    missing = [m["id"] for m, _ in CHECKS if not (FIX / m["id"] / "vulnerable").is_dir() or not (FIX / m["id"] / "safe").is_dir()]
    assert not missing, f"checks without fixtures: {missing}"


def test_checks():
    failures = []
    for meta, run in CHECKS:
        v, s = FIX / meta["id"] / "vulnerable", FIX / meta["id"] / "safe"
        if v.is_dir() and not _hits(run, v):
            failures.append(f"{meta['id']}: no hit on vulnerable fixture")
        if s.is_dir() and _hits(run, s):
            failures.append(f"{meta['id']}: false positive on safe fixture: {_hits(run, s)[0]}")
    assert not failures, "\n".join(failures)


if __name__ == "__main__":
    test_every_check_has_fixtures(); test_checks(); print(f"OK: {len(CHECKS)} checks pass their fixtures")
