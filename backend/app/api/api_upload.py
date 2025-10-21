# app/api/api_upload.py
from fastapi import APIRouter, File, UploadFile
import os

router = APIRouter(prefix="/api", tags=["upload"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"ok": True, "path": path}
