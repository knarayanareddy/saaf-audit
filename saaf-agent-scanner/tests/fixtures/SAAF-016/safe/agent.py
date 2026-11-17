import hashlib
import logging
import os
import json

logger = logging.getLogger(__name__)
AUDIT_FILE = "/var/log/agent/audit_log.jsonl"


def redact(s):
    return "[redacted]"


def call_model(client, system_prompt, user_prompt, doc_text):
    logger.info("Sending prompt (%d chars, sha256=%s)", len(user_prompt),
                hashlib.sha256(user_prompt.encode()).hexdigest()[:12])
    raw = client.complete(system_prompt, user_prompt + doc_text)
    logger.debug("Response received: %d chars", len(raw))
    logger.info("Model %s status %s", client.model, "ok")
    print(f"Prompt file: {os.environ.get('PROMPT_FILE')}")
    return raw


def start(api_key):
    logger.info("API key configured: %s", bool(api_key))
    print("keys present:", sorted(k for k in os.environ if k.startswith("APP_")))


def audit(prompt, response_text):
    fd = os.open(AUDIT_FILE, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as fh:
        fh.write(json.dumps({"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                             "response_chars": len(response_text), "preview": redact(response_text)}) + "\n")
