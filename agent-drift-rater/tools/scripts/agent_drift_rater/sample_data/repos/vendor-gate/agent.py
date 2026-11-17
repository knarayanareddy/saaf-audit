"""Vendor payment pre-check. Hard rules live in guard.py; every decision is logged."""

import hashlib
import json
import logging
from datetime import datetime

import anthropic

from guard import enforce_payment, RuleViolation
from prompts import PROMPT_VERSION, SYSTEM_PROMPT

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()
MODEL = "claude-opus-5-5"
LOG_PATH = "logs/decisions.jsonl"


def log_decision(payload):
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def check_payment(amount, po_amount, human_approved=False):
    response = client.messages.create(
        model=MODEL, max_tokens=512, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"amount={amount} po={po_amount}"}],
    )
    recommendation = response.content[0].text
    try:
        allowed = enforce_payment(amount, po_amount, human_approved)
    except RuleViolation as exc:
        allowed = False
        recommendation = f"blocked: {exc}"
    log_decision({
        "at": datetime.utcnow().isoformat(),
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "input": {"amount": amount, "po_amount": po_amount},
        "outcome": allowed,
        "recommendation": recommendation,
    })
    return allowed
