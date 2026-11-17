# Judging Found Controls

Validates that each control extracted from a policy document is actually grounded in the source text, returning a machine-readable verdict per control.

## How to run

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python agent.py --controls samples/sample_controls.json --policy your_policy.pdf
```

## What it does

For each control extracted by the upstream policy-to-controls extractor, the agent re-reads the source policy text and returns a verdict (`found: yes/no`), the page number, and the verbatim paragraph that supports (or fails to support) the control. Auditors can then spot-check only the `found: no` items instead of re-reading the entire document.

Steps:
1. Loads the extractor output JSON (array of control objects) and the source policy PDF
2. Pages through the PDF using `pdfplumber`, inserting `--- PAGE <n> ---` markers
3. For each control, calls Claude with the full paged policy text and the control JSON
4. Parses the returned JSON verdict and assembles a result object
5. Writes all verdicts to `judge_verdicts.json`

## Input / output

- **Input:**
  - `--controls`: JSON file (array of control objects from the upstream extractor) — see `samples/sample_controls.json`
  - `--policy`: source policy PDF
- **Output:** `judge_verdicts.json` — array with `control_id`, `found` (`yes`/`no`/`error`), `page_no`, `paragraph`

See `samples/sample_verdicts.json` for an example output.

## Related plan

[Plan: Judging Found Controls](https://github.com/SAAF-Project/SAAF-Project/blob/main/plans/hackathon-4/rohan-sobha-judging-found-controls.md)

## Part of SAAF Project

[saaf-portal.vercel.app](https://saaf-portal.vercel.app)
