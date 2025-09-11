from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import rest, ws
from fastapi.responses import HTMLResponse 

app = FastAPI(title="Motion Backend")
# 'static' 폴더를 '/static' 경로에 마운트합니다.
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(rest.router, prefix="/api")
app.include_router(ws.router)

@app.get("/webcam", response_class=HTMLResponse) 
async def read_root(): 
    with open("app/static/index.html", "r", encoding="utf-8") as f: 
        return HTMLResponse(content=f.read(), status_code=200) 