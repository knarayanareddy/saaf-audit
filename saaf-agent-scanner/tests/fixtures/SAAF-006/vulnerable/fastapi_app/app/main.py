from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
ITEMS = {}


@app.post("/api/items", status_code=201)
def create_item(item: dict):
    ITEMS[item["id"]] = item
    return item


@app.delete("/api/items/{item_id}")
def delete_item(item_id: str):
    ITEMS.pop(item_id, None)
    return {"deleted": item_id}


@app.post("/api/upload")
async def upload(f: UploadFile):
    return {"size": len(await f.read())}
