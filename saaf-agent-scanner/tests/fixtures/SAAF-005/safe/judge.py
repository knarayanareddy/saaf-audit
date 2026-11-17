import json
import anthropic


def judge(client, control):
    msg = client.messages.create(model="claude-x", max_tokens=300,
                                 messages=[{"role": "user", "content": str(control)}])
    return json.loads(msg.content[0].text)


def run(client, controls):
    out = []
    for control in controls:
        verdict = judge(client, control)
        clean = {"found": verdict["found"], "page_no": verdict["page_no"]}
        out.append({**clean, "control_id": control["id"]})
    return out
