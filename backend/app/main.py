from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import rest, ws

app = FastAPI(title="Motion Backend")
# 'static' 폴더를 '/static' 경로에 마운트합니다.
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(rest.router, prefix="/api")
app.include_router(ws.router)