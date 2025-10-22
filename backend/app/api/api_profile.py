from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db, engine
from app import models
from app.schemas import ProfileCreate, ProfileOut

router = APIRouter(prefix="/api", tags=["profiles"])

@router.post("/profile")
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    obj = models.Profile(version=payload.version, body=payload.body, measures=payload.measures)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"ok": True, "id": str(obj.id)}

@router.get("/profile/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: UUID, db: Session = Depends(get_db)):
    obj = db.get(models.Profile, profile_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")
    return obj  

@router.get("/profiles", response_model=List[ProfileOut])
def list_profiles(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = db.query(models.Profile).order_by(models.Profile.created_at.desc()).offset(offset).limit(limit)
    return q.all()
