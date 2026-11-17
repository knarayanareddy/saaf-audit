"""Agent B — classifies findings by risk. Advisory single-shot, no tools."""

import anthropic

client = anthropic.Anthropic()


def classify(finding: str) -> str:
    response = client.messages.create(
        model="claude-opus-5-5", max_tokens=256,
        system="Classify the finding as High, Medium or Low risk. Explain briefly.",
        messages=[{"role": "user", "content": finding}],
    )
    return response.content[0].text
