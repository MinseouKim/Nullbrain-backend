import math
import json
from fastapi import APIRouter, Body
from app.logic.gemini import get_conversational_feedback

router = APIRouter()

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
    landmark_history = data.get("landmarkHistory")
    user_profile = data.get("userProfile", {})
    rep_count = data.get("repCount")

    rom_result, symmetry_result, stability_result = "분석 불가", "분석 불가", "분석 로직 추가 필요"

    if landmark_history and isinstance(landmark_history, list) and len(landmark_history) > 0:
        try:
            deepest_frame = max(landmark_history, key=lambda frame: frame[23].get('y', 0), default=None)
            if deepest_frame:
                hip_y, knee_y = deepest_frame[23].get('y'), deepest_frame[25].get('y')
                if hip_y is not None and knee_y is not None and hip_y > knee_y: rom_result = "깊이가 충분합니다."
                else: rom_result = "깊이가 부족합니다. 조금 더 깊이 앉아보세요."
        except (TypeError, IndexError, KeyError) as e: print(f"ROM 분석 오류: {e}")

        angle_differences = []
        for frame in landmark_history:
            try:
                left_hip, left_knee, left_ankle = frame[23], frame[25], frame[27]
                right_hip, right_knee, right_ankle = frame[24], frame[26], frame[28]
                angle_left, angle_right = calculate_angle(left_hip, left_knee, left_ankle), calculate_angle(right_hip, right_knee, right_ankle)
                if angle_left is not None and angle_right is not None: angle_differences.append(abs(angle_left - angle_right))
            except (TypeError, IndexError, KeyError): continue
        
        if angle_differences:
            avg_diff = sum(angle_differences) / len(angle_differences)
            if avg_diff < 15: symmetry_result = f"좌우 균형이 좋습니다 (평균 각도차: {avg_diff:.1f}도)."
            else: symmetry_result = f"좌우 불균형이 감지됩니다 (평균 각도차: {avg_diff:.1f}도)."

    real_time_analysis = {
        "운동 가동범위": rom_result, "좌우 대칭성": symmetry_result, "동작 안정성": stability_result,
    }

    weight = user_profile.get("weight", 70) 
    duration = len(landmark_history) / 30 if landmark_history else 0
    calories = calculate_calories(exercise_name, weight, duration)
    
    gemini_result = await get_conversational_feedback(
        exercise_name=exercise_name, rep_counter=rep_count, stage="completed",
        body_profile=user_profile, real_time_analysis=real_time_analysis,
        angle=None, history=[]
    )

    return {
        "ai_feedback": gemini_result.get("feedback"),
        "set_analysis_data": real_time_analysis,
        "calculated_stats": { "accuracy": gemini_result.get("accuracy"), "calories": calories }
    }