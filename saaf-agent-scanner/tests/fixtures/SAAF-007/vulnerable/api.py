import httpx
from fastapi import FastAPI, Form
from pydantic import BaseModel

app = FastAPI()


class Job(BaseModel):
    url: str


@app.post("/ingest")
async def ingest(job: Job):
    async with httpx.AsyncClient() as client:
        r = await client.get(job.url)
    return {"len": len(r.text)}


@app.post("/hook")
async def hook(callback_url: str = Form(...)):
    return httpx.post(callback_url, json={"ok": True}).status_code


@tool
def fetch_page(url: str) -> str:
    """LLM tool: fetch a web page."""
    import requests
    return requests.get(url, timeout=5).text
