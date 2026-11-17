import requests
from fastapi import FastAPI, UploadFile, HTTPException, Depends
from slowapi import Limiter
import anthropic

app = FastAPI()
limiter = Limiter(key_func=lambda r: "ip")
client = anthropic.Anthropic()
MAX_UPLOAD_BYTES = 1_000_000


@app.post("/analyze")
@limiter.limit("5/minute")
async def analyze(file: UploadFile):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "too large")
    resp = client.messages.create(model="claude-x", max_tokens=500,
                                  messages=[{"role": "user", "content": raw.decode()[:20000]}])
    return {"result": resp.content[0].text}


def call_raw(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", json={"prompt": prompt}, timeout=30)
    return r.json()
