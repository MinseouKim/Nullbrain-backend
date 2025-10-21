# app/api/api_measure.py
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.logic.profile_loader import load_profile_from_db

router = APIRouter(prefix="/api", tags=["measure"])

@router.get("/measure/profile")
def get_latest_profile(db: Session = Depends(get_db)) -> dict:
    """
    DB에서 가장 최근 체형 분석(Profile) 데이터를 조회합니다.
    """
    try:
        return load_profile_from_db(db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/measure/analyze")
def analyze_with_db(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    DB 기반 체형분석 예시 — 프론트에서 landmarkHistory 등을 보낼 때 참고
    """
    profile = load_profile_from_db(db)
    measures = profile["measures"]

    # 예시 로직 (기존 dummy 예제 재활용)
    upper_arm_delta = abs(measures.get("upperArmL", 0) - measures.get("upperArmR", 0))
    pelvis_tilt = measures.get("pelvis_delta_px", 0)

    return {
        "upper_arm_delta": upper_arm_delta,
        "pelvis_tilt": pelvis_tilt,
        "profile_id": profile["id"],
        "received_payload": payload,
    }
