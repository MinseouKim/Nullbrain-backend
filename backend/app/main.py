from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import ws, pose, profile , pose_ws

app = FastAPI(title="Motion Backend (YOLOv8-Pose)")

# 정적파일
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 라우터
app.include_router(ws.router)
app.include_router(pose.router)
app.include_router(profile.router)
app.include_router(pose_ws.router)

@app.get("/")
def root():
    return {"ok": True, "msg": "See /static/pose-overlay.html"}
