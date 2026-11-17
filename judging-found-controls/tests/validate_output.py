"""
CI test: validates the structure of judge_verdicts.json.

Corresponds to test plan item 3:
    Verdicts for each control contain control_id, found, page_no, paragraph
"""
import json
import sys
from pathlib import Path

path = Path("judge_verdicts.json")
if not path.exists():
    sys.exit(f"ERROR: {path} not found — run run_agent_mocked.py first")

verdicts = json.loads(path.read_text())
assert isinstance(verdicts, list), "Output must be a JSON array"

for i, v in enumerate(verdicts):
    for key in ("control_id", "found", "page_no", "paragraph"):
        assert key in v, f"Verdict {i} missing key '{key}': {v}"
    assert v["found"] in ("yes", "no", "error"), (
        f"Verdict {i}: invalid found value '{v['found']}'"
    )
    assert isinstance(v["page_no"], int), (
        f"Verdict {i}: page_no must be int, got {type(v['page_no'])}"
    )
    assert isinstance(v["paragraph"], str), (
        f"Verdict {i}: paragraph must be str, got {type(v['paragraph'])}"
    )

print(f"OK: all {len(verdicts)} verdicts are well-formed")
