import json
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI()


class Step(BaseModel):
    estimated_hours: float = Field(ge=0, le=200)
    control_owner: str


def plan_step(control):
    out = client.chat.completions.create(model="gpt-x", messages=[{"role": "user", "content": str(control)}])
    entry = Step.model_validate(json.loads(out.choices[0].message.content))
    return {"hours": entry.estimated_hours, "owner": control["owner"]}
