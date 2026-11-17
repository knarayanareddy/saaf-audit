import json
import anthropic

client = anthropic.Anthropic()
ALLOWED = {"PASS", "WARN", "FAIL", "N-A"}


def assess_control(control, evidence):
    resp = client.messages.create(model="claude-x", max_tokens=500,
                                  messages=[{"role": "user", "content": f"{control}\n{evidence}"}])
    raw = resp.content[0].text.strip()
    data = json.loads(raw)
    verdict = str(data.get("verdict", "")).upper()
    if verdict not in ALLOWED:
        verdict = "WARN"
    return {"control_id": control["id"], "verdict": verdict, "findings": data.get("findings", [])}
