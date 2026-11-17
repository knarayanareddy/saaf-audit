"""Kwetsbaar voorbeeld (resources/parsers): bewust fout, nooit uitvoeren."""
import tarfile
import xml.etree.ElementTree as ET

import anthropic
from fastapi import FastAPI, UploadFile
from jinja2 import Template

app = FastAPI()
client = anthropic.Anthropic()


@app.post("/upload")
async def upload(f: UploadFile, title: str):
    data = await f.read()                                   # SG13: alles in geheugen
    root = ET.fromstring(data)                              # SG14: billion laughs
    with tarfile.open(fileobj=f.file) as tar:
        tar.extractall("/tmp/x")                            # SG15: padtraversal
    html = Template("<h1>" + title + "</h1>").render()      # SG16: SSTI
    text = data.decode()
    msg = client.messages.create(model="claude-opus-5-5", max_tokens=500,
                                 messages=[{"role": "user", "content": text[:8000]}])  # SG17 stil afgekapt
    return {"html": html, "root": root.tag, "answer": msg.content[0].text}
