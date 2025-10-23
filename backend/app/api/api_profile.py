# app/api/api_profile.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app import models

router = APIRouter(prefix="/api", tags=["profiles"])

@router.post("/profile")
def create_profile(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Body 예:
    {
      "userId": "dev-user-01",
      "version": 2,
      "body": {"height_cm": 175},
      "measures": {...}   # MeasureOrchestrator 결과(베이스라인)
    }
    """
    user_id = payload.get("userId")
    version = payload.get("version", 1)
    body = payload.get("body", {})
    measures = payload.get("measures")

    if measures is None:
        return {"ok": False, "error": "measures missing"}

    obj = models.Profile(
        user_id=user_id,     # ✅ 저장
        version=version,
        body=body,
        measures=measures,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"ok": True, "id": str(obj.id)}

@router.get("/profile/{profile_id}")
def get_profile(profile_id: UUID, db: Session = Depends(get_db)):
    obj = db.get(models.Profile, profile_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")
    return obj

@router.get("/profiles")
def list_profiles(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = db.query(models.Profile).order_by(models.Profile.created_at.desc()).offset(offset).limit(limit)
    return q.all()
