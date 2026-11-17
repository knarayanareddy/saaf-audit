import json
import logging
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

logger = logging.getLogger(__name__)


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def extract_json(raw: str):
    """Extract JSON from Claude response, stripping markdown fences and preamble.
    Handles truncated JSON by salvaging complete objects from the array."""
    raw = raw.strip()
    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if match:
        raw = match.group(1).strip()
    # Find first [ or { and try to parse
    for i, ch in enumerate(raw):
        if ch in ("[", "{"):
            try:
                return json.loads(raw[i:])
            except json.JSONDecodeError:
                # If it's a truncated array, try to salvage complete objects
                if ch == "[":
                    return _salvage_truncated_array(raw[i:])
                continue
    return json.loads(raw)


def extract_json_list(raw: str) -> list:
    """Like extract_json, but always returns a list of records.
    A bare object is wrapped; an object holding a "findings" list is unwrapped."""
    data = extract_json(raw)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("findings"), list):
            return data["findings"]
        return [data]
    raise ValueError(f"Expected a JSON array or object, got {type(data).__name__}")


def _salvage_truncated_array(raw: str) -> list:
    """Extract complete JSON objects from a truncated array.
    When Claude hits max_tokens, the JSON array gets cut off mid-object.
    This finds all complete objects and returns them."""
    results = []
    depth = 0
    obj_start = None

    for i, ch in enumerate(raw):
        if ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    obj = json.loads(raw[obj_start:i + 1])
                    results.append(obj)
                except json.JSONDecodeError:
                    pass
                obj_start = None

    if not results:
        raise json.JSONDecodeError("No complete JSON objects found", raw, 0)
    logger.warning(
        "Model response was truncated; salvaged %d complete record(s). "
        "Findings after the cut-off are missing from this run.",
        len(results),
    )
    return results
