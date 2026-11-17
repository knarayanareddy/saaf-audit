import json
from openai import OpenAI

client = OpenAI()


def plan_step(control):
    out = client.chat.completions.create(model="gpt-x", messages=[{"role": "user", "content": str(control)}])
    entry = json.loads(out.choices[0].message.content)
    entry["total"] = entry["estimated_hours"] * 2
    owner = entry.get("control_owner")
    return {**entry, "owner": owner}
