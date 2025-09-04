from fastapi import FastAPI
from app.api import rest, ws

app = FastAPI(title="Motion Backend")

app.include_router(rest.router, prefix="/api")
app.include_router(ws.router)
