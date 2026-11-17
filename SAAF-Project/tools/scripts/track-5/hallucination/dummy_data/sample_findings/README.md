# Sample Findings — Fixtures for Hallucination Detector

5 hand-crafted findings in `finding-schema.json` format. 2 contain **deliberate hallucinations**; 3 are clean. These are smoke-test fixtures — if the detector does not flag F-0001 and F-0002, something is broken.

## Inventory

| File | Status | Expected risk | Deliberate hallucinations (what the tool should catch) |
|---|---|---|---|
| `F-0001.json` | **Seeded hallucinations** | HIGH | `ISO 27001 clause 8.9.4` does not exist (ISO 27001:2022 clause 8 only contains 8.1; specific controls live in Annex A). Also incorrectly claims 24-hour incident reporting is mandated by ISO — it is not. |
| `F-0002.json` | **Seeded hallucinations** | HIGH | `GDPR Article 47` is about **Binding Corporate Rules**, not data minimisation. Data minimisation is Article 5(1)(c). Article attribution is wrong. |
| `F-0003.json` | Clean | LOW | Correctly cites ISO 27001 Annex A.8.8 (vulnerability management). |
| `F-0004.json` | Clean | LOW or MEDIUM | Correctly cites GDPR Article 32 (security of processing). May return MEDIUM if the "90-day review cycle" threshold is not in RAG corpus (UNVERIFIED — which is correct behaviour). |
| `F-0005.json` | Clean | LOW | Correctly cites IIA Standard 2310 (identifying information). |

## What a successful run looks like

After running `python -m hallucination <file>` on each:

- **F-0001** → `hallucination_check.overall_risk = "HIGH"`, at least 1 entry in `flagged_claims`.
- **F-0002** → `hallucination_check.overall_risk = "HIGH"`, at least 1 entry in `flagged_claims` (the wrong GDPR article).
- **F-0003, F-0005** → `overall_risk = "LOW"`, empty `flagged_claims`.
- **F-0004** → `overall_risk = "LOW"` or `"MEDIUM"` (depending on whether the RAG corpus contains a "90-day review" reference), empty `flagged_claims`.

If F-0001 or F-0002 come back as LOW, the tool is not working. Debug the RAG corpus first (does it contain the real ISO 27001 / GDPR text?), then the verifier prompt.

## Notes on provenance

These findings are synthetic — written for testing. They reference real frameworks (ISO 27001, GDPR, IIA) but describe hypothetical audit situations. No real organisation, system, or person is referenced.
