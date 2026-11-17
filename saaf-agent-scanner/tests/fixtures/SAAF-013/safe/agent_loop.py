import time
import anthropic

client = anthropic.Anthropic(api_key="sk-fake-example", timeout=30.0)
MAX_TURNS = 8


def run_agent(task):
    messages = [{"role": "user", "content": task}]
    for turn in range(MAX_TURNS):
        resp = client.messages.create(model="claude-x", max_tokens=1000, messages=messages)
        if resp.stop_reason != "tool_use":
            return resp
        messages.append({"role": "assistant", "content": resp.content})
    raise RuntimeError("max turns exceeded")


def retry_bounded(prompt, max_attempts=3):
    attempt = 0
    while True:
        attempt += 1
        try:
            return client.messages.create(model="claude-x", max_tokens=10, messages=[{"role": "user", "content": prompt}])
        except Exception:
            if attempt >= max_attempts:
                raise
            time.sleep(2 ** attempt)


def wait_batch(batch_id, timeout_s=3600):
    deadline = time.monotonic() + timeout_s
    batch = client.messages.batches.retrieve(batch_id)
    while batch.processing_status != "ended":
        if time.monotonic() > deadline:
            client.messages.batches.cancel(batch_id)
            raise TimeoutError
        time.sleep(10)
        batch = client.messages.batches.retrieve(batch_id)
    return batch
