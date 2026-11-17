import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
ORIGINS = [o for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
# Do not use allow_origins=["*"] here.
