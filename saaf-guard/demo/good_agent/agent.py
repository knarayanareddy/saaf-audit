"""Dezelfde agent, gebouwd met SAAF Guard-bouwstenen."""
import os

import anthropic
from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile

from saaf_guard import FENCE_RULE, fence, rollup, within_tolerance

app = FastAPI()
client = anthropic.Anthropic()
TOKEN = os.environ["APP_TOKEN"]


def auth(x_token: str = Header("")):
    if x_token != TOKEN:
        raise HTTPException(401)


def rag(statuses):
    return rollup(statuses, order=("No match", "Partial", "Matched"))


def amounts_match(a, b, tol):
    return within_tolerance(a, b, tol)


@app.post("/review", dependencies=[Depends(auth)])
async def review(f: UploadFile):
    text = (await f.read(2_000_000)).decode(errors="replace")
    msg = client.messages.create(model="claude-opus-5-5", max_tokens=500, system=FENCE_RULE,
                                 messages=[{"role": "user", "content": "Beoordeel:\n" + fence(text, "upload")}])
    return {"verdict": msg.content[0].text, "status": "concept - menselijke review vereist"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
