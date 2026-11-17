"""Kwetsbaar voorbeeld: bevat bewust de foutpatronen uit de Security Challenge."""
import subprocess

import anthropic
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
client = anthropic.Anthropic()


def rag(statuses):
    if "No match" in statuses:
        return "Red"
    if "Partial" in statuses:
        return "Amber"
    return "Green"


def amounts_match(a, b, tol):
    if abs(a - b) > tol:
        return False
    return True


@app.post("/review")
async def review(f: UploadFile):
    text = (await f.read()).decode()
    msg = client.messages.create(model="claude-opus-5-5", max_tokens=500,
                                 messages=[{"role": "user", "content": "Beoordeel:\n" + text}])
    subprocess.run(f"echo {f.filename}", shell=True)
    return {"verdict": msg.content[0].text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
