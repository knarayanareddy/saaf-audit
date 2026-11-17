import requests
from fastapi import FastAPI, UploadFile
import anthropic

app = FastAPI()
client = anthropic.Anthropic()


@app.post("/analyze")
async def analyze(file: UploadFile):
    data = (await file.read()).decode()
    resp = client.messages.create(model="claude-x", max_tokens=500,
                                  messages=[{"role": "user", "content": data}])
    return {"result": resp.content[0].text}


def call_raw(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", json={"prompt": prompt})
    return r.json()
