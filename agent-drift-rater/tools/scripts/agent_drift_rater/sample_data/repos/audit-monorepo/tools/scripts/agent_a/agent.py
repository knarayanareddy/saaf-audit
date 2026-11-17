"""Agent A — drafts control descriptions. Advisory; writes only to the outputs directory."""

import json

import anthropic

client = anthropic.Anthropic()


def draft(control_id: str) -> str:
    response = client.messages.create(
        model="claude-opus-5-5", max_tokens=512,
        system="Draft a concise control description for the given control id.",
        messages=[{"role": "user", "content": control_id}],
    )
    text = response.content[0].text
    with open("outputs/draft.json", "w", encoding="utf-8") as handle:
        json.dump({"control": control_id, "text": text}, handle)
    return text
