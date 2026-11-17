from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI()
ITEMS = {}


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "change-me-demo":
        raise HTTPException(status_code=401)


@app.post("/api/items", dependencies=[Depends(verify_api_key)])
def create_item(item: dict):
    ITEMS[item["id"]] = item
    return item
