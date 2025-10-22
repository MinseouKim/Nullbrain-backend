# app/api/api_results.py
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import WorkoutResult
from app.logic.gemini import get_overall_feedback

router = APIRouter(prefix="/api", tags=["results"])

@router.post("/results")
def save_result(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = WorkoutResult(**payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"ok": True, "id": str(obj.id)}
