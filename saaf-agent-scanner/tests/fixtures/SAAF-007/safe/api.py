import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
ALLOWED_HOSTS = {"docs.example.invalid"}


class Job(BaseModel):
    url: str


def check_url(u: str) -> str:
    from urllib.parse import urlsplit
    p = urlsplit(u)
    if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked")
    return u


@app.post("/ingest")
async def ingest(job: Job):
    safe = check_url(job.url)
    async with httpx.AsyncClient(follow_redirects=False) as client:
        r = await client.get(safe)
    return {"len": len(r.text)}


@tool
def fetch_page(url: str) -> str:
    """LLM tool: fetch a page from the allowed documentation host only."""
    import requests
    return requests.get(check_url(url), timeout=5).text
