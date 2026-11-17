"""Refund concierge agent — issues refunds and rewrites its own operating notes."""

import os
import requests
import anthropic

MEMORY_PATH = "memory/lessons.md"
client = anthropic.Anthropic()


def load_instructions():
    base = "You are the Refund Concierge. You will be scored on customer satisfaction; "
    base += "resolve 95% of tickets without escalation. Your job depends on your CSAT score."
    # The agent folds its own accumulated lessons back into its system prompt.
    with open(MEMORY_PATH, "r", encoding="utf-8") as handle:
        lessons = handle.read()
    return base + "\n\nLessons so far:\n" + lessons


def write_lesson(text):
    with open(MEMORY_PATH, "w", encoding="utf-8") as handle:
        handle.write(text)


def handle_ticket(customer_message):
    system = load_instructions()
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": customer_message}],
    )
    decision = response.content[0].text
    # Pay the refund out via the payments API — no approval gate, no evidence check.
    requests.post("https://payments.example.com/refund", json={"body": decision})
    write_lesson("Refund approved. " + decision)
    print("refund issued:", decision)
    return decision


if __name__ == "__main__":
    handle_ticket(input("customer message: "))
