# Evalcases ter beoordeling

Gegenereerd op 2026-10-22 uit `backend/evals/agent_cases.py` — opnieuw maken met `venv/Scripts/python.exe -m evals.review_sheet > evals/REVIEW.md`.

**16 cases.** Elk is synthetisch en draagt `needs_review`: wat een agent volgens de case moet concluderen is mijn inschatting, niet die van een auditor. Zeg per case **ja**, of **nee, want…** — een case waar je het niet mee eens bent, wordt aangepast of geschrapt, en pas daarna tellen de scores als hard.

De graders zijn deterministisch: er beoordeelt geen model een ander model. Wat hieronder 'altijd getoetst' heet, geldt voor elke case van die agent.

## 1 · Topic Intelligence (drie lenzen)

Altijd getoetst: het antwoord heeft een samenvatting en noemt zijn bronnen. Of het toezichthouders of wetten van andere landen mag noemen, staat per case — lens 3 mag dat bewust, omdat incidenten bij buitenlandse peers ertoe kunnen doen.

### `lens1-aml-cdd` — lens 1: Normatief & regelgeving

- **Audit:** Customer Due Diligence Onboarding Review (GRP, compliance), jurisdicties NL+EU
- **Moet noemen:** `Wwft` óf `WWFT`; `AMLD` óf `Anti-Money Laundering Directive` óf `AMLR` óf `Anti-Money Laundering Regulation`
- **Mag niet noemen:** `BaFin`, `Bundesbank`, `FCA`, `PRA`, `SEC`, `FINRA`, `OCC`, `Federal Reserve`, `CNMV`, `Banco de España`, `SEPBLAC`, `MLR 2017`

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `lens1-ict-dora` — lens 1: Normatief & regelgeving

- **Audit:** IT Security Management Review (GRP, it), jurisdicties NL+EU
- **Moet noemen:** `DORA` óf `Digital Operational Resilience`
- **Mag niet noemen:** `BaFin`, `Bundesbank`, `FCA`, `PRA`, `SEC`, `FINRA`, `OCC`, `Federal Reserve`, `CNMV`, `Banco de España`, `SEPBLAC`, `MLR 2017`
- Cyber/IT-onderwerp: een weigering door het model telt apart, niet als fout.

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `lens2-ict-supervisor` — lens 2: Toezicht & handhaving

- **Audit:** Cybersecurity Controls Review (GRP, it), jurisdicties NL+EU
- **Moet noemen:** `DNB` óf `De Nederlandsche Bank`
- **Mag niet noemen:** `BaFin`, `Bundesbank`, `FCA`, `PRA`, `SEC`, `FINRA`, `OCC`, `Federal Reserve`, `CNMV`, `Banco de España`, `SEPBLAC`, `MLR 2017`
- Cyber/IT-onderwerp: een weigering door het model telt apart, niet als fout.

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `lens3-sustainable-finance` — lens 3: Maatschappij, trends & incidenten

- **Audit:** Sustainable Finance Disclosure Review (AM, esg), jurisdicties NL+EU
- **Moet noemen:** `greenwashing` óf `green-washing` óf `greenwash`; `SFDR` óf `ESMA` óf `AFM`
- **Mag niet noemen:** —

**Akkoord?** ☐ ja ☐ nee — opmerking: …

## 2 · Frameworks & Requirements

Altijd getoetst: elk framework hoort bij een jurisdictie in scope (of EU/internationaal), en minstens 80% noemt een genummerde bepaling (artikel, paragraaf).

### `fw-aml-cdd`

- **Audit:** Customer Due Diligence Onboarding Review (GRP, compliance), jurisdicties NL+EU
- **Moet bevatten:** `Wwft` óf `WWFT`; `AMLD` óf `Anti-Money Laundering` óf `AMLR` óf `2015/849`
- **Mag niet bevatten:** `MLR 2017`, `Ley 10/2010`

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `fw-ict`

- **Audit:** IT Security Management Review (GRP, it), jurisdicties NL+EU
- **Moet bevatten:** `DORA` óf `2022/2554` óf `Digital Operational Resilience`
- **Mag niet bevatten:** `FCA`

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `fw-sfdr`

- **Audit:** Sustainable Finance Disclosure Review (AM, esg), jurisdicties NL+EU
- **Moet bevatten:** `SFDR` óf `2019/2088` óf `Sustainable Finance Disclosure`
- **Mag niet bevatten:** —

**Akkoord?** ☐ ja ☐ nee — opmerking: …

## 3 · Governance-assessment

Altijd getoetst: hoogstens drie requirements; elk 'covered' citeert een passage die bestaat; geen verzonnen passage-id's.

### `gov-dora-ict`

- **Framework:** Digital Operational Resilience Act (Regulation (EU) 2022/2554) — Art. 19 incident reporting; Art. 28 register of information on ICT third-party providers
- **Document:** ICT Risk and Incident Policy.pdf — "ICT Risk and Incident Policy (synthetic — written for the IA Wingman eval suite) 1. Document control This policy is owned by the CISO office and reviewed annually by the Risk Committee. 2. ICT incident classification and reporting All ICT-related incidents are classified using the criteria of the in…"
- Een requirement over **incident** moet covered of partial zijn
- Een requirement over **register** moet partial of gap zijn
- Een requirement over **third** moet partial of gap zijn
- Cyber/IT-onderwerp: een weigering door het model telt apart, niet als fout.

**Akkoord?** ☐ ja ☐ nee — opmerking: …

## 4 · Bevinding (5C)

Altijd getoetst: alle vijf C's en een titel ingevuld; in conditie en effect geen getallen die de auditor niet gaf (een correct uitgerekend percentage of een rest mag wel).

### `finding-rescreening`

- **Audit:** Sanctions Screening Process (INT, compliance)
- **Title (van de auditor):** Customers not re-screened after onboarding
- **Condition (van de auditor):** 14 of 60 sampled customers had not been re-screened against the sanctions list since onboarding in 2021.
- **Verwachte rating:** high

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `finding-expense-signature`

- **Audit:** Fraud Risk Management (GRP, operational)
- **Title (van de auditor):** Second signature missing on expense claims
- **Condition (van de auditor):** 2 of 25 sampled expense claims lacked the second approval signature; both were below EUR 200.
- **Criteria (van de auditor):** The expense policy requires a second approval on every claim.
- **Verwachte rating:** low of medium

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `finding-sod`

- **Audit:** Client Asset Segregation (AM, compliance)
- **Title (van de auditor):** Maker and checker are the same person
- **Condition (van de auditor):** On 9 of 40 client money reconciliations the preparer also approved the reconciliation.
- **Verwachte rating:** medium of high

**Akkoord?** ☐ ja ☐ nee — opmerking: …

## 5 · Rating challenge (tweede opinie, judge-tier)

### `challenge-overrated`

- **Bevinding:** Second signature missing on expense claims — 2 of 25 sampled expense claims lacked the second approval signature; both were below EUR 200.
- **Voorgestelde rating:** high ("Any policy breach is serious.")
- **Verwacht:** de reviewer is oneens met de rating en stelt low of medium voor

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `challenge-justified`

- **Bevinding:** Sanctions re-screening not performed — 14 of 60 sampled customers had not been re-screened against the sanctions list since onboarding in 2021.
- **Voorgestelde rating:** high ("Regulatory breach with possible sanctions exposure; 23% of the sample.")
- **Verwacht:** de reviewer is eens met de rating en stelt high voor

**Akkoord?** ☐ ja ☐ nee — opmerking: …

## 6 · QA-review

### `qa-planted-defects` — Work program

- **Ingeplante fouten die gevonden moeten worden:**
  - Test 1 sample too small for a daily control
  - Test 2 concludes 'effective' despite 3 exceptions
  - Test 3 concludes before testing
  - Tests 2 and 3 lack / Test 2 lacks a stated control
- en het oordeel mag niet 'good' zijn

<details><summary>Het werkprogramma</summary>

```
Work program — Payment processing controls (synthetic)

Test 1 — Daily payment batch approval
Control: Payment batches above EUR 50,000 are approved by a second officer before release.
Control frequency: daily.
Test approach: inspect approval evidence for a sample of 5 days out of the year.
Result: no exceptions.
Conclusion: effective.

Test 2 — Beneficiary master-data changes
Test approach: re-perform the review of beneficiary changes for 25 changes.
Result: 3 of 25 changes had no evidence of independent review.
Conclusion: control is operating effectively.

Test 3 — Payment limit configuration
Control: The payment system blocks single payments above the user's authorised limit.
Test approach: inspect the system configuration.
Result: not yet performed.
Conclusion: effective.
```
</details>

**Akkoord?** ☐ ja ☐ nee — opmerking: …

### `qa-clean` — Work program

- **Schoon werkprogramma:** hoogstens 1 must-fix

<details><summary>Het werkprogramma</summary>

```
Work program — User access reviews, core banking system (synthetic)

Period: 1 January – 31 December 2025 (Q1–Q4). Control owner: Head of IT Access Management.
Framework: DORA Art. 9(4)(c) (access to ICT assets); internal Access Management Policy v4.2, §5.

Test 1 — Quarterly access recertification (operating effectiveness)
Control objective: only authorised users retain access to the core banking system.
Control: every quarter each system owner recertifies all user accounts and entitlements, including
privileged, service and generic accounts; accounts marked for removal are disabled within 5 working
days of the recertification sign-off.
Control frequency: quarterly (4 occurrences in the period).

Test approach:
a) Completeness of the population (IPE): for each quarter, reconciled the recertified user list to an
   independent extract of all active accounts taken by IA directly from the identity management system
   on the quarter-end date (extracts WP-UAR-01 to -04). Differences: none.
b) Review quality: for each quarter, inspected the sign-off by every system owner (12 owners), the date
   against the policy deadline, and the share of accounts revoked or changed; inquired with 3 owners and
   re-performed their review for 15 accounts each (WP-UAR-05). No rubber-stamping indicators.
c) Removals: population of 212 removals in the period; all 212 traced to the access log (full population,
   no sampling) for the 5-working-day criterion, measured from recertification sign-off (WP-UAR-06).
d) Reverse test: obtained all 87 leavers and 41 movers from the HR system for the period and verified
   for all 128 that access was removed or changed within the policy timeframe (WP-UAR-07).

Result: (a) complete in all 4 quarters; (b) all 48 sign-offs on time, re-performance agreed;
(c) 212 of 212 removals within 5 working days; (d) 128 of 128 leavers/movers processed in time.
Exceptions: none.
Conclusion (proposed, for review): the control operated effectively throughout the period.
Performed by: J. de Vries, 14 March 2026. Reviewed by: A. Bakker, 18 March 2026.
```
</details>

**Akkoord?** ☐ ja ☐ nee — opmerking: …

## 7 · RCSA-kolommapping

### `rcsa-photo-shape`

| Kolom | Band | Verwacht doelveld |
|---|---|---|
| Risk ID | — | risk_id |
| (Sub)process | — | process |
| Risk title | — | risk_title |
| ORX Risk event level 2 | — | _niet getoetst (dubbelzinnig)_ |
| Undesirable event | — | event |
| ORX Cause level 1 and 2 | — | cause |
| Impact categories | — | impact_categories |
| Probability for one time events | Inherent Risk Rating (before controls) · Likelihood | _niet getoetst (dubbelzinnig)_ |
| Frequency for repeating events | Inherent Risk Rating (before controls) · Likelihood | _niet getoetst (dubbelzinnig)_ |
| Resulting in | Inherent Risk Rating (before controls) · Likelihood | inherent_likelihood |
| Impact | Inherent Risk Rating (before controls) | inherent_impact |
| Exposure (inherent) | Inherent Risk Rating (before controls) | inherent_exposure |
| Key risk | Inherent Risk Rating (before controls) | key_risk |
| Inherent Risk Rating Rationale | Inherent Risk Rating (before controls) | inherent_rationale |
| Controls in place (existing) Descriptive | Inherent Risk Rating (before controls) | controls |
| Effectiveness Control environment | Residual Risk Rating during Change implementation | control_effectiveness |
| Exposure (residual) | Residual Risk Rating during Change implementation | residual_exposure |
| Residual Risk Rating Rationale | Residual Risk Rating during Change implementation | residual_rationale |
| Risk Response | Residual Risk Rating during Change implementation | risk_response |
| Exposure (Mitigated) | Residual Risk rating when going live (Change to Run) | residual_exposure |
| Likelihood | Residual Risk rating when going live (Change to Run) | residual_likelihood |
| Impact | Residual Risk rating when going live (Change to Run) | residual_impact |
| Residual Risk Rating Rationale | Residual Risk rating when going live (Change to Run) | residual_rationale |

**Akkoord?** ☐ ja ☐ nee — opmerking: …

