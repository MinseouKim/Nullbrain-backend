import json, uuid, os
from fastapi import APIRouter, Body, HTTPException

router = APIRouter()
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

@router.post("/api/profile")
def save_profile(profile: dict = Body(...)):
    if "version" not in profile or "body" not in profile or "measures" not in profile:
        raise HTTPException(400, "invalid profile")
    pid = str(uuid.uuid4())
    path = os.path.join(DATA_DIR, f"{pid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return {"ok": True, "id": pid}

@router.get("/api/profile/{pid}")
def get_profile(pid: str):
    path = os.path.join(DATA_DIR, f"{pid}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "not found")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
# app/api_profile.py
import json, uuid, os
from fastapi import APIRouter, Body, HTTPException

router = APIRouter()
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

@router.post("/api/profile")
def save_profile(profile: dict = Body(...)):
    if "version" not in profile or "body" not in profile or "measures" not in profile:
        raise HTTPException(400, "invalid profile")
    pid = str(uuid.uuid4())
    path = os.path.join(DATA_DIR, f"{pid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return {"ok": True, "id": pid}

@router.get("/api/profile/{pid}")
def get_profile(pid: str):
    path = os.path.join(DATA_DIR, f"{pid}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "not found")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
