"""Dezelfde functies, veilig gebouwd."""
import tarfile

import anthropic
from defusedxml import ElementTree as ET
from fastapi import FastAPI, HTTPException, UploadFile
from jinja2 import Environment, select_autoescape

from saaf_guard import fence

app = FastAPI()
client = anthropic.Anthropic()
MAX_UPLOAD_BYTES = 5_000_000
env = Environment(autoescape=select_autoescape())
TITLE = env.from_string("<h1>{{ title }}</h1>")


@app.post("/upload")
async def upload(f: UploadFile, title: str):
    data = await f.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413)
    root = ET.fromstring(data)
    with tarfile.open(fileobj=f.file) as tar:
        tar.extractall("/tmp/x", filter="data")
    html = TITLE.render(title=title)
    msg = client.messages.create(model="claude-opus-5-5", max_tokens=500,
                                 messages=[{"role": "user", "content": fence(data.decode())}])
    return {"html": html, "root": root.tag, "answer": msg.content[0].text}
