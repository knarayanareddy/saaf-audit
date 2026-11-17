"""
CI test: verifies that a malformed model response is recorded as found: 'error'
without crashing the agent.

Corresponds to test plan item 4:
    Error cases (malformed model response) are captured as found: 'error' rather than crashing
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))

os.environ["ANTHROPIC_API_KEY"] = "test-key"

content_block = MagicMock()
content_block.text = "NOT VALID JSON {{{{"

mock_message = MagicMock()
mock_message.content = [content_block]

mock_client = MagicMock()
mock_client.messages.create.return_value = mock_message

output_path = Path("judge_verdicts_error_test.json")

with patch("anthropic.Anthropic", return_value=mock_client):
    import agent  # noqa: E402

    sys.argv = [
        "agent.py",
        "--controls", "samples/sample_controls.json",
        "--policy", str(Path(__file__).parent / "sample_policy.pdf"),
        "--output", str(output_path),
    ]
    agent.main()

verdicts = json.loads(output_path.read_text())
error_verdicts = [v for v in verdicts if v["found"] == "error"]
assert len(error_verdicts) == len(verdicts), (
    f"Expected all {len(verdicts)} verdicts to be 'error', "
    f"but only {len(error_verdicts)} were"
)
print(f"OK: all {len(verdicts)} verdicts correctly recorded as 'error'")
output_path.unlink()
