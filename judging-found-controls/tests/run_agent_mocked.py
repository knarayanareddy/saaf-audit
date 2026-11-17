"""
CI test: runs agent.main() with a mocked Anthropic client and asserts
that judge_verdicts.json is produced.

Corresponds to test plan item 2:
    python agent.py --controls samples/sample_controls.json --policy <pdf>
    runs and produces judge_verdicts.json
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the repo root is on the path so `import agent` works from any cwd.
sys.path.insert(0, str(Path(__file__).parents[1]))

os.environ["ANTHROPIC_API_KEY"] = "test-key"

MOCK_VERDICT = json.dumps({"found": "yes", "page_no": 1, "paragraph": "Mock paragraph."})

content_block = MagicMock()
content_block.text = MOCK_VERDICT

mock_message = MagicMock()
mock_message.content = [content_block]

mock_client = MagicMock()
mock_client.messages.create.return_value = mock_message

output_path = Path("judge_verdicts.json")

with patch("anthropic.Anthropic", return_value=mock_client):
    import agent  # noqa: E402

    sys.argv = [
        "agent.py",
        "--controls", "samples/sample_controls.json",
        "--policy", str(Path(__file__).parent / "sample_policy.pdf"),
        "--output", str(output_path),
    ]
    agent.main()

assert output_path.exists(), f"{output_path} was not produced"
verdicts = json.loads(output_path.read_text())
assert len(verdicts) == 3, f"Expected 3 verdicts, got {len(verdicts)}"
print(f"OK: {output_path} produced with {len(verdicts)} verdicts")
