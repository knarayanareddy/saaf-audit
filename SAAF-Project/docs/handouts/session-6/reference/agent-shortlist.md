---
title: "Agent Shortlist — what to stress-test"
subtitle: "SAAF Hackathon #5 · Session 6 · 16 June 2026"
---

# Agent Shortlist — what to stress-test

**First choice: an agent you built, or one you'd genuinely adopt in your own business.** That stake is where the value is. If nothing fits, pick from the shortlist below. Any SAAF repo is fair game.

Maturity is a rough guide (★ = how ready it looks), not a grade. Less mature ≠ less useful to test — early agents often have the most to find.

## Most mature (great for deep findings — A1, A2, A3)
| Agent (repo) | What it does | ★ |
|---|---|---|
| **RCM-Builder / The-Control-Freaks** | Builds a Risk & Control Matrix from audit inputs | ★★★★★ |
| **llm_owasp** | Audits an agent against the OWASP LLM Top 10 | ★★★★★ |
| **ICFCOP control-testing** | Tests one "mega-control" across multiple frameworks | ★★★★★ |
| **Vendor_Guard** | Scores suppliers / third-party risk against EU/NL frameworks | ★★★★ |

## Working, high hardening value (great for A1, A6)
| Agent (repo) | What it does | ★ |
|---|---|---|
| **Compliance-Report-Generator** | EU AI Act risk assessment + compliance report | ★★★ |
| **IA-Fieldwork-Preparation** | Prepares audit fieldwork packs | ★★★ |
| **Policy-to-Controls-Extractor** | Turns policy text into structured controls | ★★★ |
| **PBC-Assistant** | Checks "prepared-by-client" submissions for completeness | ★★★ |
| **Team-HighTable** | Continuous monitoring / anomaly detection | ★★★ |
| **WhatsTheNews** | Tracks regulatory change (DNB/AFM feeds) | ★★★ |

## Domain specialists (pick if it matches your business)
GDPR-AI-Audit-Agent · three-way-match-audit / threewaysecurity (P2P 3-way match) · CUEC_Crosscheck · ExecGRC · UC3-incident-issue-intelligence · Track-2-Evidence-Collection-Extraction · Track-2---IAM-final · Track-4-Audit-Report-Generator · Audit-Work-Program-Agent-UC-8- · Finding-analysis.

## Quality tooling — use it, don't rebuild it
**Hallucination-detection skill** (`tools/scripts/track-5/`) — handy in A1/A3 to check whether an agent's outputs invent control references or facts.

---
*All repos are under the SAAF-Project GitHub org. Use dummy/synthetic data only.*
