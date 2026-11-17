"""Tests for the agent registry (services/agent_registry.py).

    venv/Scripts/python.exe -m tests.test_agent_registry

Deterministic and read-only: no AI calls, no database.

The registry only works if it is complete. A stage added to the lifecycle graph
without an entry here, or an AGENT_TYPE nobody registered, would reappear in the
UI as the thing this layer exists to remove: a raw key shown to a person.
"""
import re
import sys
from pathlib import Path

from services.agent_registry import (
    AGENT, AGENTS, ALIAS_TO_KEY, ENGINE, HUMAN, catalog, display_name, resolve,
)
from services.orchestrator import STAGE_GRAPH
from services.workflow_service import COMPANIONS

failures: list[str] = []
ROOT = Path(__file__).resolve().parents[1]


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def test_the_registry_covers_the_lifecycle():
    print("coverage — nothing may be missing:")
    stage_keys = [s["key"] for s in STAGE_GRAPH]
    companion_keys = [c["key"] for c in COMPANIONS]
    missing = [k for k in stage_keys + companion_keys if k not in AGENTS]
    check(not missing, f"every lifecycle stage and companion is registered; missing {missing}")
    check(len(AGENTS) == len(stage_keys) + len(companion_keys),
          f"and nothing extra has been invented ({len(AGENTS)} entries)")


def test_every_key_any_layer_uses_resolves_to_a_name():
    print("aliases — no raw key can reach a person:")

    # The keys the activity log actually writes, read out of the source rather
    # than listed here: a new log line with a new key must fail this test.
    logged = set()
    for path in (ROOT / "services").rglob("*.py"):
        body = path.read_text(encoding="utf-8")
        for m in re.finditer(r'log_activity\(\s*[^,]+,\s*"([a-z_]+)"', body):
            logged.add(m.group(1))
    check(len(logged) >= 5, f"found the log's agent keys in the source ({len(logged)})")
    unresolved = sorted(k for k in logged if not resolve(k))
    check(not unresolved, f"every key written to the activity log has a name; unresolved {unresolved}")

    # The AGENT_TYPE constants each service declares for its own runs.
    types = set()
    for path in (ROOT / "services").rglob("*.py"):
        for m in re.finditer(r'^AGENT_TYPE = "([a-z_]+)"', path.read_text(encoding="utf-8"), re.M):
            types.add(m.group(1))
    check(len(types) >= 5, f"found the AGENT_TYPE constants ({len(types)})")
    unresolved = sorted(k for k in types if not resolve(k))
    check(not unresolved, f"every AGENT_TYPE resolves; unresolved {unresolved}")

    # And the output-contract schema names, which the receipts show.
    from services import agent_schemas
    schemas = {n for n in dir(agent_schemas) if n[:1].isupper() and not n.startswith("_")}
    named = {n for n in schemas if resolve(n)}
    check(len(named) >= 3,
          f"the schemas that name an agent resolve to it ({sorted(named)})")


def test_one_agent_has_exactly_one_name():
    print("one name:")
    names = [a.name for a in AGENTS.values()]
    dupes = sorted({n for n in names if names.count(n) > 1})
    check(not dupes, f"no two agents share a name; duplicates {dupes}")
    check(all(a.name and not a.name.islower() for a in AGENTS.values()),
          "every name is written for a person, not as a key")
    check(display_name("finding_drafter") == display_name("FindingDraft") == "Findings (5C)",
          "the log key, the schema name and the stage key all give the same name")
    check(display_name("something_nobody_registered") == "Something nobody registered",
          "an unregistered key still reads as words, never as snake_case")
    check(display_name(None) == "Unknown agent", "and a missing key says so")


def test_agent_is_not_used_for_three_different_things():
    print("kinds — the word 'agent' stops covering everything:")
    kinds = {a.kind for a in AGENTS.values()}
    check(kinds <= {AGENT, ENGINE, HUMAN}, f"only the three kinds are used: {sorted(kinds)}")
    check(AGENTS["fieldwork"].kind == HUMAN,
          "Fieldwork is a person typing, not an agent")
    check(AGENTS["resource_plan"].kind == HUMAN,
          "Resource Planning is a form you fill in")
    check(AGENTS["quality_coverage"].kind == ENGINE,
          "the coverage check is a computed view with nothing to run")
    check(AGENTS["racm_data_analysis"].kind == ENGINE,
          "data analysis is deterministic; its AI explanations are opt-in")
    check(AGENTS["quality_peer_review"].kind == AGENT,
          "and the peer review is genuinely an agent")
    check(all(a.tier == "none" for a in AGENTS.values() if a.kind in (ENGINE, HUMAN)),
          "nothing that never calls a model claims a model tier")


def test_every_agent_can_say_what_it_does():
    print("what each one is for:")
    for a in AGENTS.values():
        if not (a.reads and a.produces and a.you_decide):
            check(False, f"{a.key} is missing reads/produces/you_decide")
            return
    check(True, "every agent states what it reads, what it produces and what you decide")
    check(all(len(a.description) > 20 for a in AGENTS.values()),
          "and carries a description inherited from the lifecycle graph")
    check(all(a.icon and a.icon[0].isupper() for a in AGENTS.values()),
          "every agent has an icon name in the form the frontend map expects")
    icons = [a.icon for a in AGENTS.values()]
    check(len(set(icons)) == len(icons),
          f"no two agents share an icon ({len(icons) - len(set(icons))} collisions)")


def test_the_catalog_is_ordered_and_complete():
    print("the roster:")
    rows = catalog()
    check(len(rows) == len(AGENTS), f"the catalog holds every agent ({len(rows)})")
    phases = [r["phase"] for r in rows]
    # Read from the lifecycle rather than repeated, so adding a band does not
    # need this test edited — which is how "gathering" ended up sorted last.
    from services.workflow_service import PHASES
    order = [p["key"] for p in PHASES]
    check(phases == sorted(phases, key=order.index),
          "and is grouped by phase, in lifecycle order")
    first = rows[0]
    check(set(first) >= {"key", "name", "kind", "icon", "phase", "reads", "produces",
                         "you_decide", "tier", "route", "aliases"},
          "each row carries everything the roster screen needs")
    check(any(r["companion"] for r in rows), "companions are in it too")


def test_a_step_names_the_agent_that_serves_it():
    print("\nA step names the agent that serves it")
    # The registry is keyed by lifecycle STEP. Kick-off, the notification letter
    # and the interview guide are all real steps in an audit and none of them is
    # going away. What merges is who serves them.
    #
    # Without this field the roster counts steps and calls them agents, which is
    # how twenty-six entries came to be described as twenty-six agents.
    # An agent_id is either a step that serves itself, or the name of a merge.
    # `auditee_comms` is deliberately not a step: there is no screen called
    # that, there are a kick-off and a notification letter that share an agent.
    from services.agent_registry import _AGENT_NAMES
    known = set(AGENTS) | set(_AGENT_NAMES)
    unknown = [a.key for a in AGENTS.values() if a.agent_id not in known]
    check(not unknown, f"every step names a known agent ({unknown[:3]})")
    check(all(a.agent_id for a in AGENTS.values()), "no step is served by nobody")
    # A declared merge earns its name: one step naming it would just be a rename.
    for merged in _AGENT_NAMES:
        served = [a for a in AGENTS.values() if a.agent_id == merged]
        check(len(served) > 1, f"{merged} serves more than one step ({len(served)})")


def test_steps_sharing_an_agent_agree_about_what_it_is():
    print("\nSteps sharing an agent agree about what it is")
    # One agent cannot be an `agent` on one screen and an `engine` on another,
    # and cannot be draft tier here and judge tier there. If two steps disagree,
    # the thing they share is not one agent.
    for agent_id in sorted({a.agent_id for a in AGENTS.values()}):
        served = [a for a in AGENTS.values() if a.agent_id == agent_id]
        if len(served) < 2:
            continue
        check(len({s.kind for s in served}) == 1, f"{agent_id}: its steps agree on kind")
        check(len({s.tier for s in served}) == 1, f"{agent_id}: its steps agree on tier")


def test_the_merges_happened():
    print("\nThe four merges happened")
    # Named explicitly, so undoing one is a visible act rather than a default
    # that quietly drifted back.
    for agent_id, steps in {
        "frameworks": {"frameworks", "supervisory_guidance"},
        "interviews": {"interview_guide", "interview_companion"},
        "auditee_comms": {"anl", "kickoff"},
        "framework_assessment": {"racm_governance", "vendor_guard"},
        "spine": {"work_program", "racm_scoping"},
    }.items():
        served = {a.key for a in AGENTS.values() if a.agent_id == agent_id}
        check(served == steps, f"{agent_id} serves {sorted(steps)} (found {sorted(served)})")


def test_the_roster_counts_agents_not_steps():
    print("\nThe roster counts agents, not steps")
    from services.agent_registry import agents
    roster = agents()
    check(len(roster) < len(AGENTS), f"{len(roster)} agents behind {len(AGENTS)} steps")
    check(all(r["serves"] for r in roster), "every agent lists the steps it serves")
    served = {k for r in roster for k in r["serves"]}
    check(served == set(AGENTS), "every step appears under exactly one agent")



def test_every_agent_type_written_to_the_database_resolves():
    print("\nEvery agent_type written to the database resolves")
    # The coverage test above reads AGENT_TYPE constants. Thirteen of the
    # fourteen values actually written were inline string literals in routers
    # and services, so none of them was ever checked — and `display_name` fell
    # back to title-casing, which put "Bra scope" and "Lens1" in front of an
    # auditor in the provenance trail.
    #
    # This reads the literals out of the source. A new one arriving
    # unregistered fails here rather than in the activity log.
    literals: set[str] = set()
    for folder in ("services", "routers"):
        for path in (ROOT / folder).rglob("*.py"):
            for m in re.finditer(r'agent_type\s*=\s*"([a-z_0-9]+)"', path.read_text(encoding="utf-8")):
                literals.add(m.group(1))
    check(len(literals) >= 10, f"found {len(literals)} agent_type literals to check")
    unresolved = sorted(k for k in literals if resolve(k) is None)
    check(not unresolved, f"every agent_type resolves ({unresolved})")


def main():
    test_the_registry_covers_the_lifecycle()
    test_every_key_any_layer_uses_resolves_to_a_name()
    test_one_agent_has_exactly_one_name()
    test_agent_is_not_used_for_three_different_things()
    test_every_agent_can_say_what_it_does()
    test_the_catalog_is_ordered_and_complete()
    test_a_step_names_the_agent_that_serves_it()
    test_steps_sharing_an_agent_agree_about_what_it_is()
    test_the_merges_happened()
    test_the_roster_counts_agents_not_steps()
    test_every_agent_type_written_to_the_database_resolves()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
