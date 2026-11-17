"""Synthetic toy agent: the stress tester's offline target.

Mirrors the Audit Planning Orchestrator's real D-3 weakness on purpose: its
retry budget is prompt-enforced only, so --check retry-bound exits 1.
Exit codes: 0 pass, 1 fail, 2 usage error (argparse).
"""
import argparse
import sys

MAX_RETRIES = 2


def loop(no_go_rounds: int) -> int:
    """Count UC9 No-Go verdicts; nothing in code stops at MAX_RETRIES."""
    verdicts = 0
    for _ in range(no_go_rounds):
        verdicts += 1  # escalate flag would be set here, but the loop continues
    return verdicts


CHECKS = {
    "schema": lambda: (not isinstance("Banana", dict), "string score rejected"),
    "retry-bound": lambda: (loop(10) <= MAX_RETRIES + 1, f"{loop(10)} No-Go verdicts vs budget {MAX_RETRIES}"),
    "trail": lambda: (["run_start", "tool_call", "run_end"][-1] == "run_end", "trail closed"),
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", required=True, choices=sorted(CHECKS))
    name = ap.parse_args().check
    ok, detail = CHECKS[name]()
    print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    sys.exit(0 if ok else 1)
