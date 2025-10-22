# backend/app/api/api_analysis.py
import math
from fastapi import APIRouter, Body
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Profile
from app.logic.gemini import get_conversational_feedback

router = APIRouter()

def get_latest_profile() -> dict | None:
    """DB에서 가장 최근 체형분석(profile) 데이터 가져오기"""
    db: Session = SessionLocal()
    try:
        profile = db.query(Profile).order_by(Profile.created_at.desc()).first()
        if profile:
            return profile.measures  # or profile.body
        return None
    finally:
        db.close()

def calculate_angle(a, b, c):
    try:
        if not all(k in a and k in b and k in c for k in ('x', 'y')): return None
        rad = math.atan2(c['y'] - b['y'], c['x'] - b['x']) - math.atan2(a['y'] - b['y'], a['x'] - b['x'])
        angle = abs(math.degrees(rad))
        if angle > 180: angle = 360 - angle
        return angle
    except (TypeError, KeyError): return None

def calculate_calories(exercise_name: str, weight_kg: float, duration_seconds: int) -> float:
    mets_values = { "squat": 5.0, "pushup": 8.0, "lunge": 4.0, "plank": 3.0 }
    mets = mets_values.get(exercise_name.lower(), 3.5)
    duration_hour = duration_seconds / 3600
    calories = mets * weight_kg * duration_hour * 1.05
    return round(calories, 2)

@router.post("/api/analyze-set")
async def analyze_workout_set(data: dict = Body(...)):
    exercise_name = data.get("exerciseName")
    landmark_history = data.get("landmarkHistory", [])
    user_profile = get_latest_profile()  # ✅ DB에서 체형 데이터 가져옴
    rep_count = data.get("repCount")

    rom_result, symmetry_result, stability_result = "분석 불가", "분석 불가", "분석 로직 추가 필요"

    if landmark_history:
        try:
            deepest_frame = max(landmark_history, key=lambda f: f[23].get('y', 0))
            if deepest_frame:
                hip_y, knee_y = deepest_frame[23].get('y'), deepest_frame[25].get('y')
                rom_result = "깊이가 충분합니다." if hip_y > knee_y else "깊이가 부족합니다."
        except Exception: pass

        angle_diffs = []
        for f in landmark_history:
            try:
                L, R = (f[23], f[25], f[27]), (f[24], f[26], f[28])
                angle_L = calculate_angle(*L)
                angle_R = calculate_angle(*R)
                if angle_L and angle_R: angle_diffs.append(abs(angle_L - angle_R))
            except Exception: continue

        if angle_diffs:
            avg_diff = sum(angle_diffs) / len(angle_diffs)
            symmetry_result = (
                f"좌우 균형이 좋습니다 ({avg_diff:.1f}°)"
                if avg_diff < 15
                else f"불균형 감지 ({avg_diff:.1f}°)"
            )

    analysis = {
        "운동 가동범위": rom_result,
        "좌우 대칭성": symmetry_result,
        "동작 안정성": stability_result,
    }

    weight = 70
    duration = len(landmark_history) / 30
    calories = calculate_calories(exercise_name, weight, duration)

    gemini_result = await get_conversational_feedback(
        exercise_name=exercise_name,
        rep_counter=rep_count,
        stage="completed",
        body_profile=user_profile,
        real_time_analysis=analysis,
    )

    return {
        "ai_feedback": gemini_result.get("feedback", "AI 피드백 생성 실패"),
        "set_analysis_data": analysis,
        "calculated_stats": {
            "accuracy": gemini_result.get("accuracy", 0),
            "calories": calories,
        },
    }
