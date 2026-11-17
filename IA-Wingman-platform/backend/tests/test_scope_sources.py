"""Where a scope item came from (services/scope_sources.py).

    venv/Scripts/python.exe -m tests.test_scope_sources

The stop criterion for this phase is that an auditor can name, from the map
alone, which step produced any given scope item. Three things have to hold for
that, and each has a test here:

  1. every writer names a step this module knows — enforced by reading the
     source of the routers, because a writer that invents a string is exactly
     how `cascaded` came to mean three different producers;
  2. every step it names exists in the agent registry, so the label on the item
     and the label on the map cannot drift apart;
  3. an unknown source degrades to "origin not recorded" rather than to
     something that looks like an answer.
"""
import sys
from pathlib import Path

from services import scope_sources as ss
from services.agent_registry import AGENTS

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


BACKEND = Path(__file__).resolve().parent.parent
WRITERS = [
    "routers/planning.py",
    "routers/kickoff.py",
    "routers/bra.py",
    "services/golden_path_service.py",
    "seed_demo_esg.py",
]


def _calls(text: str, name: str) -> list[str]:
    """Every `name(...)` call in the file, as source, with parentheses balanced."""
    out, start = [], text.find(name)
    while start != -1:
        i, depth = start + len(name) - 1, 0
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append(text[start:i + 1])
        start = text.find(name, i)
    return out


def main() -> None:
    print("\nthe vocabulary:")
    check(len(ss.SOURCES) == len({s.key for s in ss.SOURCES}), "every key is distinct")
    check(all(ss.normalise(s.key) == s.key for s in ss.SOURCES),
          "and normalises to itself")
    check(ss.normalise("nonsense") == "" and ss.normalise(None) == "",
          "an unknown source normalises to empty, not to a guess")

    print("\nevery source names a step the registry knows:")
    for source in ss.SOURCES:
        if not source.step:
            check(bool(source.own_label),
                  f"{source.key} has no step, so it carries its own label")
            continue
        check(source.step in AGENTS, f"{source.key} -> {source.step} is a real step")
        check(ss.label(source.key) == AGENTS[source.step].label,
              f"{source.key}'s label is the registry's, not a second copy")

    print("\nan unrecorded origin says so:")
    check(ss.label("cascaded") == ss.UNKNOWN_LABEL,
          "the old ambiguous string is not silently translated")
    check(ss.step_of("cascaded") == "", "and resolves to no step")
    described = ss.describe("cascaded")
    check(described["source"] == "cascaded",
          "describe() still reports what is stored, so the row stays traceable")
    check(described["source_label"] == ss.UNKNOWN_LABEL, "with an honest label")

    print("\nstamp() refuses what it cannot name:")
    try:
        ss.stamp("something_new")
        check(False, "an unknown source raises")
    except ValueError as exc:
        check("not a scope source" in str(exc), "an unknown source raises, and says why")
    check(ss.stamp(ss.MANUAL) == {"source": "manual", "source_ref": None},
          "a source with no upstream row stores no ref rather than an empty one")
    check(ss.stamp(ss.BRA, "run-7")["source_ref"] == "run-7",
          "and carries the ref when there is one")

    print("\nno writer names its own source:")
    # Reading the writers is the point. A test that only exercised stamp()
    # would pass while a router quietly kept source="cascaded".
    # ApplicableFramework has a `source` column of its own with its own
    # vocabulary, so this looks only inside the two constructors that matter.
    for rel in WRITERS:
        text = (BACKEND / rel).read_text(encoding="utf-8")
        calls = [c for name in ("ScopeItem(", "KeyAuditQuestion(") for c in _calls(text, name)]
        check(bool(calls), f"{rel} still writes scope rows")
        unstamped = [c for c in calls if "scope_sources.stamp(" not in c]
        check(not unstamped,
              f"{rel}: all {len(calls)} scope writes go through stamp()")
        check(not [c for c in calls if "source=" in c],
              f"{rel} sets no source literal of its own")

    print("\nthe browser gets the same list:")
    # The frontend cannot import this module, so it reads a fixture. The fixture
    # is only worth having if something fails when it goes stale.
    import json

    fixture = BACKEND.parent / "frontend" / "tests" / "fixtures" / "scope-sources.json"
    check(fixture.exists(), "frontend/tests/fixtures/scope-sources.json exists")
    if fixture.exists():
        expected = [{"key": s.key, "step": s.step, "label": ss.label(s.key)} for s in ss.SOURCES]
        check(json.loads(fixture.read_text(encoding="utf-8")) == expected,
              "fixture matches SOURCES — regenerate it when a producer is added")

    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
