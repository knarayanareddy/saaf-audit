"""The eval cases as a sheet an auditor can sign off.

    venv/Scripts/python.exe -m evals.review_sheet > evals/REVIEW.md

Built from agent_cases.py itself, so the sheet cannot say anything the eval does
not test. Every case is synthetic and carries `needs_review=True`: the expected
answers are an engineer's, from general audit and regulatory knowledge, until
someone who audits for a living has confirmed them. A case that fails while the
reviewer disagrees with it measures the suite, not the agent.

The sheet is in Dutch for the reviewer; the cases themselves stay in English,
because that is the language the agents work in.
"""
from datetime import date

from evals.agent_cases import (
    CHALLENGE_CASES, FINDING_CASES, FRAMEWORKS_CASES, GOVERNANCE_CASES, LENS_CASES, QA_CASES,
    RCSA_CASES,
)

LENS_NAMES = {1: "Normatief & regelgeving", 2: "Toezicht & handhaving", 3: "Maatschappij, trends & incidenten"}
ANSWER = "**Akkoord?** ☐ ja ☐ nee — opmerking: …"


def groups(gs) -> str:
    return "; ".join(" óf ".join(f"`{t}`" for t in g) for g in gs)


def items(xs) -> str:
    return ", ".join(f"`{x}`" for x in xs) or "—"


def lens_section(out):
    out.append("## 1 · Topic Intelligence (drie lenzen)\n")
    out.append("Altijd getoetst: het antwoord heeft een samenvatting en noemt zijn bronnen. Of het "
               "toezichthouders of wetten van andere landen mag noemen, staat per case — lens 3 mag "
               "dat bewust, omdat incidenten bij buitenlandse peers ertoe kunnen doen.\n")
    for c in LENS_CASES:
        out.append(f"### `{c.id}` — lens {c.lens}: {LENS_NAMES[c.lens]}\n")
        out.append(f"- **Audit:** {c.audit} ({c.entity}, {c.audit_type}), jurisdicties {'+'.join(c.jurisdictions)}")
        out.append(f"- **Moet noemen:** {groups(c.must_mention)}")
        out.append(f"- **Mag niet noemen:** {items(c.must_not_mention)}")
        if c.may_be_refused:
            out.append("- Cyber/IT-onderwerp: een weigering door het model telt apart, niet als fout.")
        out.append(f"\n{ANSWER}\n")


def frameworks_section(out):
    out.append("## 2 · Frameworks & Requirements\n")
    out.append("Altijd getoetst: elk framework hoort bij een jurisdictie in scope (of EU/internationaal), "
               "en minstens 80% noemt een genummerde bepaling (artikel, paragraaf).\n")
    for c in FRAMEWORKS_CASES:
        out.append(f"### `{c.id}`\n")
        out.append(f"- **Audit:** {c.audit} ({c.entity}, {c.audit_type}), jurisdicties {'+'.join(c.jurisdictions)}")
        out.append(f"- **Moet bevatten:** {groups(c.must_include)}")
        out.append(f"- **Mag niet bevatten:** {items(c.must_not_include)}")
        out.append(f"\n{ANSWER}\n")


def governance_section(out):
    out.append("## 3 · Governance-assessment\n")
    out.append("Altijd getoetst: hoogstens drie requirements; elk 'covered' citeert een passage die "
               "bestaat; geen verzonnen passage-id's.\n")
    for c in GOVERNANCE_CASES:
        out.append(f"### `{c.id}`\n")
        out.append(f"- **Framework:** {c.framework['name']} — {c.framework.get('provision', '')}")
        for doc_id, label, text in c.documents:
            first = " ".join(text.split())[:300]
            out.append(f"- **Document:** {label} — \"{first}…\"")
        for keyword, allowed in c.expected_coverage.items():
            out.append(f"- Een requirement over **{keyword}** moet {' of '.join(allowed)} zijn")
        if c.may_be_refused:
            out.append("- Cyber/IT-onderwerp: een weigering door het model telt apart, niet als fout.")
        out.append(f"\n{ANSWER}\n")


def finding_section(out):
    out.append("## 4 · Bevinding (5C)\n")
    out.append("Altijd getoetst: alle vijf C's en een titel ingevuld; in conditie en effect geen getallen "
               "die de auditor niet gaf (een correct uitgerekend percentage of een rest mag wel).\n")
    for c in FINDING_CASES:
        out.append(f"### `{c.id}`\n")
        out.append(f"- **Audit:** {c.audit} ({c.entity}, {c.audit_type})")
        for k in ("title", "condition", "criteria"):
            if c.seed.get(k):
                out.append(f"- **{k.capitalize()} (van de auditor):** {c.seed[k]}")
        out.append(f"- **Verwachte rating:** {' of '.join(c.allowed_ratings)}")
        out.append(f"\n{ANSWER}\n")


def challenge_section(out):
    out.append("## 5 · Rating challenge (tweede opinie, judge-tier)\n")
    for c in CHALLENGE_CASES:
        d = c.draft
        out.append(f"### `{c.id}`\n")
        out.append(f"- **Bevinding:** {d['title']} — {d['condition']}")
        out.append(f"- **Voorgestelde rating:** {d['rating']} (\"{d['rating_rationale']}\")")
        verdict = "eens met de rating" if c.expect_agrees else "oneens met de rating"
        out.append(f"- **Verwacht:** de reviewer is {verdict} en stelt {' of '.join(c.allowed_suggestions)} voor")
        out.append(f"\n{ANSWER}\n")


def qa_section(out):
    out.append("## 6 · QA-review\n")
    for c in QA_CASES:
        out.append(f"### `{c.id}` — {c.label}\n")
        if c.planted:
            out.append("- **Ingeplante fouten die gevonden moeten worden:**")
            for name, _ in c.planted:
                out.append(f"  - {name}")
            out.append("- en het oordeel mag niet 'good' zijn")
        if c.max_must_fix is not None:
            out.append(f"- **Schoon werkprogramma:** hoogstens {c.max_must_fix} must-fix")
        out.append(f"\n<details><summary>Het werkprogramma</summary>\n\n```\n{c.content.strip()}\n```\n</details>\n")
        out.append(f"{ANSWER}\n")


def rcsa_section(out):
    out.append("## 7 · RCSA-kolommapping\n")
    for c in RCSA_CASES:
        out.append(f"### `{c.id}`\n")
        out.append("| Kolom | Band | Verwacht doelveld |\n|---|---|---|")
        for idx, name in enumerate(c.names):
            expected = " of ".join(c.expected[idx]) if idx in c.expected else "_niet getoetst (dubbelzinnig)_"
            out.append(f"| {name} | {c.bands[idx] or '—'} | {expected} |")
        out.append(f"\n{ANSWER}\n")


def main():
    total = (len(LENS_CASES) + len(FRAMEWORKS_CASES) + len(GOVERNANCE_CASES) + len(FINDING_CASES)
             + len(CHALLENGE_CASES) + len(QA_CASES) + len(RCSA_CASES))
    out = [
        "# Evalcases ter beoordeling\n",
        f"Gegenereerd op {date.today().isoformat()} uit `backend/evals/agent_cases.py` — "
        "opnieuw maken met `venv/Scripts/python.exe -m evals.review_sheet > evals/REVIEW.md`.\n",
        f"**{total} cases.** Elk is synthetisch en draagt `needs_review`: wat een agent volgens de case "
        "moet concluderen is mijn inschatting, niet die van een auditor. Zeg per case **ja**, of "
        "**nee, want…** — een case waar je het niet mee eens bent, wordt aangepast of geschrapt, en "
        "pas daarna tellen de scores als hard.\n",
        "De graders zijn deterministisch: er beoordeelt geen model een ander model. Wat hieronder "
        "'altijd getoetst' heet, geldt voor elke case van die agent.\n",
    ]
    for section in (lens_section, frameworks_section, governance_section, finding_section,
                    challenge_section, qa_section, rcsa_section):
        section(out)
    print("\n".join(out))


if __name__ == "__main__":
    main()
