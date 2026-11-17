import time
import anthropic

client = anthropic.Anthropic(api_key="sk-fake-example")


def run_agent(task):
    messages = [{"role": "user", "content": task}]
    while True:
        resp = client.messages.create(model="claude-x", max_tokens=1000, messages=messages)
        if resp.stop_reason != "tool_use":
            return resp
        messages.append({"role": "assistant", "content": resp.content})


def retry_forever(prompt):
    while True:
        try:
            return client.messages.create(model="claude-x", max_tokens=10, messages=[{"role": "user", "content": prompt}])
        except Exception:
            time.sleep(1)


def wait_batch(batch_id):
    batch = client.messages.batches.retrieve(batch_id)
    while batch.processing_status != "ended":
        time.sleep(10)
        batch = client.messages.batches.retrieve(batch_id)
    return batch
