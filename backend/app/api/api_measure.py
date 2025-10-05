# api/api_measure.py
from fastapi import APIRouter, Body
from app.logic import load_dummy_profile


router = APIRouter(prefix="/api")

@router.get("/measure/dummy")
def get_dummy_measure() -> dict:
    """
    더미 체형분석 결과 조회 (DB 대신 JSON에서 읽기)
    """
    return load_dummy_profile()

@router.post("/measure/analyze")
def analyze_with_dummy(payload: dict = Body(...)) -> dict:
    """
    더미데이터 기반 분석 예시
    """
    profile = load_dummy_profile()

    # 예시 로직: 좌우 상완 길이 차이
    upper_arm_delta = abs(profile["lengths_cm"]["upperArmL"] - profile["lengths_cm"]["upperArmR"])
    # 예시 로직: 골반 기울기
    pelvis_tilt = profile["symmetry"]["pelvis_delta_px"]

    return {
        "upper_arm_delta": upper_arm_delta,
        "pelvis_tilt": pelvis_tilt,
        "raw_profile": profile,
        "received_payload": payload,  # 프론트에서 landmarkHistory 같은 걸 보낼 때 확인용
    }
