import logging
import os
import json
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)
AUDIT_FILE = "audit_log.jsonl"


def call_model(client, system_prompt, user_prompt, doc_text):
    logger.info("Sending prompt: %s", user_prompt)
    raw = client.complete(system_prompt, user_prompt + doc_text)
    logger.debug("Full raw response:\n%s", raw)
    print(f"DEBUG messages: {user_prompt}")
    return raw


def start(api_key):
    logger.info(f"Using key {api_key}")
    print("env:", dict(os.environ))


def audit(prompt, response_text):
    with open(AUDIT_FILE, "a") as fh:
        fh.write(json.dumps({"prompt": prompt, "response": response_text}) + "\n")
